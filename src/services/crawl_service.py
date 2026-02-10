"""크롤링 오케스트레이션 서비스

여러 사이트에서 동시에 크롤링하고 결과를 취합한다.
"""
import asyncio
import logging
from typing import List

from crawlers import BaseCrawler, RawConcertData, InterparkCrawler, MelonCrawler

logger = logging.getLogger(__name__)


class CrawlService:
    """여러 크롤러를 관리하고 병렬 실행"""

    def __init__(self):
        self.crawlers: List[BaseCrawler] = [
            InterparkCrawler(),
            MelonCrawler(),
        ]

    async def crawl_all(self, artist_name: str) -> List[RawConcertData]:
        """모든 크롤러로 동시 검색 후 결과 취합"""
        tasks = [crawler.search(artist_name) for crawler in self.crawlers]
        results_per_site = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: List[RawConcertData] = []
        for i, result in enumerate(results_per_site):
            crawler_name = self.crawlers[i].source_name
            if isinstance(result, Exception):
                logger.error(f"[{crawler_name}] 크롤링 실패: {result}")
                continue
            all_results.extend(result)

        logger.info(f"크롤링 완료 '{artist_name}': 총 {len(all_results)}건 수집")
        return all_results
