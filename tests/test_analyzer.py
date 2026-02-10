"""AI 분석기 테스트

google-genai SDK의 import 문제를 mock으로 우회하여 파싱/프롬프트 로직을 테스트한다.
"""
import sys
import pytest
from unittest.mock import MagicMock

# google.genai import를 mock 처리 (테스트 환경에서 cryptography 충돌 방지)
mock_genai = MagicMock()
sys.modules["google.genai"] = mock_genai
sys.modules["google"] = MagicMock(genai=mock_genai)

from crawlers.base import RawConcertData
from services.concert_analyzer import ConcertAnalyzer


class TestParseResponse:
    """AI 응답 JSON 파싱 테스트"""

    def setup_method(self):
        self.analyzer = ConcertAnalyzer()

    def test_parse_plain_json(self):
        text = '[{"concert_title": "Test Concert", "confidence": 0.9}]'
        result = self.analyzer._parse_response(text)
        assert len(result) == 1
        assert result[0]["concert_title"] == "Test Concert"

    def test_parse_json_in_markdown_block(self):
        text = '```json\n[{"concert_title": "Test"}]\n```'
        result = self.analyzer._parse_response(text)
        assert len(result) == 1

    def test_parse_json_in_generic_code_block(self):
        text = '```\n[{"concert_title": "Test"}]\n```'
        result = self.analyzer._parse_response(text)
        assert len(result) == 1

    def test_parse_single_object_wrapped_in_list(self):
        text = '{"concert_title": "Single"}'
        result = self.analyzer._parse_response(text)
        assert isinstance(result, list)
        assert result[0]["concert_title"] == "Single"

    def test_parse_empty_array(self):
        text = "[]"
        result = self.analyzer._parse_response(text)
        assert result == []

    def test_parse_invalid_json_raises(self):
        with pytest.raises(Exception):
            self.analyzer._parse_response("not json at all")


class TestBuildAnalysisPrompt:
    """분석 프롬프트 생성 테스트"""

    def setup_method(self):
        self.analyzer = ConcertAnalyzer()

    def test_prompt_contains_artist_name(self):
        prompt = self.analyzer._build_analysis_prompt("아이유", "[]")
        assert "아이유" in prompt

    def test_prompt_contains_crawled_data(self):
        data = '[{"title": "아이유 콘서트"}]'
        prompt = self.analyzer._build_analysis_prompt("아이유", data)
        assert "아이유 콘서트" in prompt

    def test_prompt_contains_instructions(self):
        prompt = self.analyzer._build_analysis_prompt("테스트", "[]")
        assert "중복" in prompt
        assert "신뢰도" in prompt
        assert "confidence" in prompt
