"""크롤러 파싱 로직 단위 테스트"""
import pytest
from crawlers.base import RawConcertData
from crawlers.interpark import InterparkCrawler
from crawlers.melon import MelonCrawler


class TestRawConcertData:
    """RawConcertData 데이터클래스 테스트"""

    def test_to_dict(self):
        data = RawConcertData(
            title="BTS 콘서트",
            artist_name="BTS",
            venue="잠실종합운동장",
            source_site="interpark",
        )
        d = data.to_dict()
        assert d["title"] == "BTS 콘서트"
        assert d["artist_name"] == "BTS"
        assert d["venue"] == "잠실종합운동장"
        assert d["source_site"] == "interpark"

    def test_optional_fields_default_none(self):
        data = RawConcertData(title="Test", artist_name="Test")
        assert data.venue is None
        assert data.date is None
        assert data.time is None
        assert data.price is None
        assert data.booking_url is None

    def test_extra_field(self):
        data = RawConcertData(
            title="Test",
            artist_name="Test",
            extra={"rating": 5},
        )
        assert data.extra["rating"] == 5


class TestInterparkCrawler:
    """인터파크 크롤러 파싱 테스트"""

    def setup_method(self):
        self.crawler = InterparkCrawler()

    def test_source_name(self):
        assert self.crawler.source_name == "interpark"

    def test_parse_search_results_with_items(self):
        """검색 결과 항목이 있는 HTML 파싱"""
        html = """
        <html><body>
        <ul>
            <li class="prd_item">
                <a class="prd_name" href="/ticket/1234">아이유 콘서트 2026</a>
                <span class="venue">KSPO DOME</span>
                <span class="date">2026.05.01 ~ 2026.05.03</span>
            </li>
            <li class="prd_item">
                <a class="prd_name" href="/ticket/5678">아이유 팬미팅</a>
                <span class="place">올림픽홀</span>
                <span class="period">2026.06.15</span>
            </li>
        </ul>
        </body></html>
        """
        results = self.crawler._parse_search_results(html, "아이유")
        assert len(results) == 2
        assert results[0].title == "아이유 콘서트 2026"
        assert results[0].venue == "KSPO DOME"
        assert results[0].date == "2026.05.01 ~ 2026.05.03"
        assert results[0].source_site == "interpark"
        assert "1234" in results[0].booking_url

    def test_parse_search_results_empty_html(self):
        """결과 없는 HTML 파싱"""
        html = "<html><body><p>검색 결과가 없습니다</p></body></html>"
        results = self.crawler._parse_search_results(html, "없는가수")
        assert results == []

    def test_parse_item_no_title(self):
        """제목 없는 항목은 무시"""
        from bs4 import BeautifulSoup
        html = '<li class="prd_item"><span class="venue">장소</span></li>'
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("li")
        result = self.crawler._parse_item(item, "테스트")
        assert result is None

    def test_parse_item_with_full_url(self):
        """이미 전체 URL인 경우 그대로 사용"""
        from bs4 import BeautifulSoup
        html = '<li class="prd_item"><a class="prd_name" href="https://example.com/ticket">콘서트</a></li>'
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("li")
        result = self.crawler._parse_item(item, "테스트")
        assert result.booking_url == "https://example.com/ticket"


class TestMelonCrawler:
    """멜론 크롤러 파싱 테스트"""

    def setup_method(self):
        self.crawler = MelonCrawler()

    def test_source_name(self):
        assert self.crawler.source_name == "melon"

    def test_parse_search_results_with_items(self):
        """검색 결과 항목이 있는 HTML 파싱"""
        html = """
        <html><body>
        <ul class="list_ticket">
            <li>
                <a class="tit" href="/performance/detail/9999">BTS World Tour Seoul</a>
                <span class="venue">잠실종합운동장</span>
                <span class="date">2026.07.01</span>
                <span class="price">165,000원</span>
            </li>
        </ul>
        </body></html>
        """
        results = self.crawler._parse_search_results(html, "BTS")
        assert len(results) == 1
        assert results[0].title == "BTS World Tour Seoul"
        assert results[0].venue == "잠실종합운동장"
        assert results[0].price == "165,000원"
        assert results[0].source_site == "melon"

    def test_parse_search_results_empty(self):
        html = "<html><body></body></html>"
        results = self.crawler._parse_search_results(html, "없는가수")
        assert results == []

    def test_parse_item_with_relative_url(self):
        """상대 URL을 절대 URL로 변환"""
        from bs4 import BeautifulSoup
        html = '<li><a class="tit" href="/detail/123">콘서트</a></li>'
        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("li")
        result = self.crawler._parse_item(item, "테스트")
        assert result.booking_url.startswith("https://ticket.melon.com")
