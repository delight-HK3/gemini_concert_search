"""크롤링 서비스 테스트"""
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

# google.genai import를 mock 처리
mock_genai = MagicMock()
sys.modules.setdefault("google.genai", mock_genai)
sys.modules.setdefault("google", MagicMock(genai=mock_genai))

from crawlers.base import RawConcertData
from services.crawl_service import CrawlService


class TestCrawlService:
    """CrawlService 단위 테스트"""

    def test_has_multiple_crawlers(self):
        service = CrawlService()
        assert len(service.crawlers) >= 2

    def test_crawler_names(self):
        service = CrawlService()
        names = [c.source_name for c in service.crawlers]
        assert "interpark" in names
        assert "melon" in names

    @pytest.mark.asyncio
    async def test_crawl_all_aggregates_results(self):
        """여러 크롤러 결과를 취합하는지 테스트"""
        service = CrawlService()

        mock_data_1 = [
            RawConcertData(title="Concert A", artist_name="IU", source_site="interpark")
        ]
        mock_data_2 = [
            RawConcertData(title="Concert B", artist_name="IU", source_site="melon")
        ]

        service.crawlers[0].search = AsyncMock(return_value=mock_data_1)
        service.crawlers[1].search = AsyncMock(return_value=mock_data_2)

        results = await service.crawl_all("IU")
        assert len(results) == 2
        assert results[0].source_site == "interpark"
        assert results[1].source_site == "melon"

    @pytest.mark.asyncio
    async def test_crawl_all_handles_crawler_failure(self):
        """한 크롤러가 실패해도 다른 결과는 유지"""
        service = CrawlService()

        mock_data = [
            RawConcertData(title="Concert", artist_name="BTS", source_site="melon")
        ]

        service.crawlers[0].search = AsyncMock(side_effect=Exception("network error"))
        service.crawlers[1].search = AsyncMock(return_value=mock_data)

        results = await service.crawl_all("BTS")
        assert len(results) == 1
        assert results[0].source_site == "melon"

    @pytest.mark.asyncio
    async def test_crawl_all_empty_results(self):
        """크롤링 결과가 없는 경우"""
        service = CrawlService()

        service.crawlers[0].search = AsyncMock(return_value=[])
        service.crawlers[1].search = AsyncMock(return_value=[])

        results = await service.crawl_all("Unknown Artist")
        assert results == []
