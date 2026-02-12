"""티켓링크 티켓 크롤러"""
import logging
from typing import List
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import BaseCrawler, RawConcertData

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.ticketlink.co.kr/search"
TIMEOUT = 15.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.ticketlink.co.kr/",
}


class TicketLinkCrawler(BaseCrawler):
    """티켓링크 검색 크롤러"""

    source_name = "ticketlink"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
        reraise=True,
    )
    async def _fetch(self, url: str, params: dict) -> str:
        """HTTP 요청 (재시도 포함)"""
        async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.text

    async def search(self, artist_name: str) -> List[RawConcertData]:
        """티켓링크에서 아티스트 콘서트 검색"""
        results: List[RawConcertData] = []

        try:
            query = f"{artist_name} 콘서트"
            html = await self._fetch(SEARCH_URL, {"keyword": query})
            results = self._parse_search_results(html, artist_name)
        except httpx.HTTPStatusError as e:
            logger.warning(f"[ticketlink] HTTP {e.response.status_code} for '{artist_name}'")
        except httpx.ConnectError:
            logger.warning(f"[ticketlink] 연결 실패 — '{artist_name}'")
        except Exception as e:
            logger.error(f"[ticketlink] 크롤링 오류 '{artist_name}': {e}")

        self._log_result(artist_name, len(results))
        return results

    def _parse_search_results(self, html: str, artist_name: str) -> List[RawConcertData]:
        """검색 결과 HTML 파싱"""
        soup = BeautifulSoup(html, "html.parser")
        results: List[RawConcertData] = []

        # 티켓링크 검색 결과 항목 파싱
        items = soup.select(
            ".search_result li, .product_list li, .list_item, "
            ".search_list li, .event_list li, .prd_list li"
        )
        for item in items:
            data = self._parse_item(item, artist_name)
            if data:
                results.append(data)

        # 대체 셀렉터 — 사이트 구조 변경 대비
        if not results:
            items = soup.select(
                "[class*='product'], [class*='event'], [class*='concert'], "
                "[class*='ticket'], [class*='search'] li"
            )
            for item in items:
                data = self._parse_item(item, artist_name)
                if data:
                    results.append(data)

        return results

    def _parse_item(self, item, artist_name: str) -> RawConcertData | None:
        """개별 검색 결과 항목 파싱"""
        # 제목 추출
        title_el = item.select_one(
            "a.prd_name, .tit a, .title a, .event_name a, "
            "h3 a, h4 a, .name a, a[class*='tit'], a[class*='name']"
        )
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        if not title:
            return None

        # 링크 추출
        href = title_el.get("href", "")
        if href and not href.startswith("http"):
            href = f"https://www.ticketlink.co.kr{href}"

        # 장소 추출
        venue = ""
        venue_el = item.select_one(
            ".venue, .place, .location, "
            "[class*='venue'], [class*='place'], [class*='location']"
        )
        if venue_el:
            venue = venue_el.get_text(strip=True)

        # 날짜 추출
        date = ""
        date_el = item.select_one(
            ".date, .period, .schedule, "
            "[class*='date'], [class*='period'], [class*='schedule']"
        )
        if date_el:
            date = date_el.get_text(strip=True)

        # 가격 추출
        price = ""
        price_el = item.select_one(".price, [class*='price']")
        if price_el:
            price = price_el.get_text(strip=True)

        return RawConcertData(
            title=title,
            artist_name=artist_name,
            venue=venue or None,
            date=date or None,
            price=price or None,
            booking_url=href or None,
            source_site=self.source_name,
        )
