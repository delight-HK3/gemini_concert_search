"""인터파크 티켓 크롤러"""
import logging
from typing import List
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import BaseCrawler, RawConcertData

logger = logging.getLogger(__name__)

SEARCH_URL = "https://tickets.interpark.com/contents/search"
TIMEOUT = 15.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


class InterparkCrawler(BaseCrawler):
    """인터파크 티켓 검색 크롤러"""

    source_name = "interpark"

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
        """인터파크에서 아티스트 콘서트 검색"""
        results: List[RawConcertData] = []

        try:
            keyword = f"{artist_name}"
            html = await self._fetch(SEARCH_URL, {"keyword": keyword})
            results = self._parse_search_results(html, artist_name)
        except httpx.HTTPStatusError as e:
            logger.warning(f"[interpark] HTTP {e.response.status_code} for '{artist_name}'")
        except httpx.ConnectError:
            logger.warning(f"[interpark] 연결 실패 — '{artist_name}'")
        except Exception as e:
            logger.error(f"[interpark] 크롤링 오류 '{artist_name}': {e}")

        results = self.filter_results(results)
        self._log_result(artist_name, len(results))
        return results

    def _parse_search_results(self, html: str, artist_name: str) -> List[RawConcertData]:
        """검색 결과 HTML 파싱"""
        soup = BeautifulSoup(html, "html.parser")
        results: List[RawConcertData] = []

        # 인터파크 티켓: a[class*='TicketItem_ticketItem'] 구조
        items = soup.select("a[class*='TicketItem_ticketItem']")
        for item in items:
            data = self._parse_item(item, artist_name)
            if data:
                results.append(data)

        return results

    def _parse_item(self, item, artist_name: str) -> RawConcertData | None:
        """개별 검색 결과 항목 파싱 (TicketItem 요소)"""
        # 제목: data-prd-name 속성 우선, 없으면 goodsName 요소
        title = item.get("data-prd-name", "")
        if not title:
            title_el = item.select_one("[class*='TicketItem_goodsName']")
            if title_el:
                title = title_el.get_text(strip=True)
        if not title:
            return None

        # 링크: data-prd-no로 상품 페이지 URL 생성
        prd_no = item.get("data-prd-no", "")
        href = f"https://tickets.interpark.com/goods/{prd_no}" if prd_no else ""

        # 장소
        venue = ""
        venue_el = item.select_one("[class*='TicketItem_placeName']")
        if venue_el:
            venue = venue_el.get_text(strip=True)

        # 날짜
        date = ""
        date_el = item.select_one("[class*='TicketItem_playDate']")
        if date_el:
            date = date_el.get_text(strip=True)

        return RawConcertData(
            title=title,
            artist_name=artist_name,
            venue=venue or None,
            date=date or None,
            booking_url=href or None,
            source_site=self.source_name,
        )
