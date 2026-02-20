"""yes24 티켓 크롤러"""
import logging
import re
from typing import List
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import BaseCrawler, RawConcertData

logger = logging.getLogger(__name__)

SEARCH_URL = "https://ticket.yes24.com/search"
TIMEOUT = 15.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://ticket.yes24.com/",
    "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}


class Yes24Crawler(BaseCrawler):
    """Yes24 티켓 검색 크롤러"""

    source_name = "yes24"

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
        """Yes24에서 아티스트 콘서트 검색"""
        results: List[RawConcertData] = []

        try:
            url = f"{SEARCH_URL}/{quote(artist_name)}"
            html = await self._fetch(url, {})
            results = self._parse_search_results(html, artist_name)
        except httpx.HTTPStatusError as e:
            logger.warning(f"[yes24] HTTP {e.response.status_code} for '{artist_name}'")
        except httpx.ConnectError:
            logger.warning(f"[yes24] 연결 실패 — '{artist_name}'")
        except Exception as e:
            logger.error(f"[yes24] 크롤링 오류 '{artist_name}': {e}")

        results = self.filter_results(results)
        self._log_result(artist_name, len(results))
        return results

    def _parse_search_results(self, html: str, artist_name: str) -> List[RawConcertData]:
        """검색 결과 HTML 파싱"""
        soup = BeautifulSoup(html, "html.parser")
        results: List[RawConcertData] = []

        # Yes24 실제 구조: div.srch-list-item (display:none 템플릿 제외)
        items = soup.select(".srch-list-item")
        for item in items:
            if "display:none" in (item.get("style") or "").replace(" ", ""):
                continue
            data = self._parse_item(item, artist_name)
            if data:
                results.append(data)

        return results

    def _parse_item(self, item, artist_name: str) -> RawConcertData | None:
        """개별 검색 결과 항목 파싱

        Yes24 검색 결과 구조:
          div.srch-list-item
            div > a > img           (포스터)
            div
              p.item-tit > a        (제목 + 링크)
            div                     (날짜, 클래스 없음)
            div                     (장소, 클래스 없음)
        """
        # 제목·링크 추출 — p.item-tit 안의 a 태그
        title_el = item.select_one(".item-tit a")
        if not title_el:
            return None

        title = " ".join(title_el.get_text().split())
        if not title:
            return None

        href = title_el.get("href", "")
        if href and not href.startswith("http"):
            href = f"https://ticket.yes24.com{href}"

        # 날짜·장소 추출 — 자식 요소 없이 텍스트만 가진 div에서 추출
        date = None
        venue = None
        for div in item.find_all("div", recursive=False):
            # 자식 요소(p, a, img 등)가 있는 div는 건너뜀 → 텍스트 전용 div만 대상
            if div.find(True):
                continue
            text = div.get_text(strip=True)
            if not text:
                continue
            # 날짜 패턴: 2026.03.28 또는 2026.03.28~2026.03.29
            if re.search(r"\d{4}\.\d{2}\.\d{2}", text):
                date = text
            else:
                venue = text

        return RawConcertData(
            title=title,
            artist_name=artist_name,
            venue=venue,
            date=date,
            price=None,
            booking_url=href or None,
            source_site=self.source_name,
        )
