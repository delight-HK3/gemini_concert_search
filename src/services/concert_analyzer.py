"""AI 콘서트 데이터 분석 서비스

크롤링된 원본 데이터를 Gemini AI로 분석·정제·보강한다.
역할: 데이터 정제, 중복 판별, 정보 보강, 신뢰도 평가
"""
from google import genai
import json
import logging
import time
import re
from typing import List, Dict
from core.config import settings
from crawlers.base import RawConcertData

logger = logging.getLogger(__name__)


class ConcertAnalyzer:
    """Gemini AI를 사용한 크롤링 데이터 분석기"""

    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not set. AI analysis disabled.")
            self.client = None
            return

        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    def _generate_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Gemini API 호출 (429 rate limit 시 자동 재시도)"""
        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=settings.AI_MODEL,
                    contents=prompt,
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries:
                    # retryDelay 파싱 시도, 실패 시 기본 25초
                    wait_seconds = 25
                    match = re.search(r'retry.*?(\d+)', error_str, re.IGNORECASE)
                    if match:
                        wait_seconds = int(match.group(1)) + 5
                    logger.info(f"Rate limit 도달, {wait_seconds}초 후 재시도 ({attempt + 1}/{max_retries})")
                    time.sleep(wait_seconds)
                else:
                    raise

    def analyze(self, artist_name: str, raw_data: List[RawConcertData]) -> List[Dict]:
        """크롤링 데이터를 AI로 분석·정제·병합

        Args:
            artist_name: 아티스트 이름
            raw_data: 여러 사이트에서 크롤링한 원본 데이터

        Returns:
            정제된 콘서트 정보 목록 (중복 제거, 신뢰도 포함)
        """
        if not self.client:
            return []

        if not raw_data:
            return self._fallback_search(artist_name)

        try:
            serialized = json.dumps(
                [d.to_dict() for d in raw_data], ensure_ascii=False, indent=2
            )

            prompt = self.build_analysis_prompt(artist_name, serialized)
            text = self._generate_with_retry(prompt)
            return self.parse_response(text)

        except Exception as e:
            logger.error(f"AI 분석 오류 '{artist_name}': {e}")
            return []

    def _fallback_search(self, artist_name: str) -> List[Dict]:
        """크롤링 데이터가 없을 때 AI 직접 검색 (폴백)"""
        if not self.client:
            return []

        try:
            prompt = f""""{artist_name}"의 한국 내한 콘서트(공연) 정보를 검색해서 알려주세요.

다음 정보를 JSON 배열 형식으로 제공하세요:
- concert_title: 콘서트/공연 제목
- venue: 공연 장소
- concert_date: 공연 날짜 (예: "2026-03-15")
- concert_time: 공연 시간 (예: "19:00")
- ticket_price: 티켓 가격
- booking_date: 예매 시작일
- booking_url: 예매 링크
- source: "ai_search"
- confidence: 0.3
- data_sources: "ai_only"
- is_verified: false

확인된 정보가 없으면 빈 배열 []을 반환하세요.
추측이나 가짜 정보는 절대 포함하지 마세요.
JSON 배열만 출력하세요."""

            text = self._generate_with_retry(prompt)
            return self.parse_response(text)

        except Exception as e:
            logger.error(f"AI 폴백 검색 오류 '{artist_name}': {e}")
            return []

    def build_analysis_prompt(self, artist_name: str, crawled_json: str) -> str:
        """AI 분석 프롬프트 생성"""
        return f"""다음은 여러 티켓 사이트에서 크롤링한 "{artist_name}"의 콘서트 원본 데이터입니다:

{crawled_json}

위 데이터를 분석하여 다음 작업을 수행하세요:

1. **중복 판별·병합**: 여러 사이트에서 가져온 같은 공연을 하나로 병합
2. **데이터 정제**: 날짜(YYYY-MM-DD), 시간(HH:MM), 가격 형식을 통일
3. **정보 보강**: 한 사이트에 없는 정보를 다른 사이트 데이터로 보완
4. **신뢰도 평가**: 여러 사이트에서 확인된 정보는 높은 신뢰도, 단일 소스는 낮은 신뢰도

결과를 다음 JSON 배열 형식으로 출력하세요:
[
  {{
    "concert_title": "콘서트 제목",
    "venue": "공연 장소",
    "concert_date": "2026-03-15",
    "concert_time": "19:00",
    "ticket_price": "VIP 198,000원 / R석 165,000원",
    "booking_date": "예매 시작일",
    "booking_url": "예매 링크",
    "source": "분석 요약",
    "confidence": 0.85,
    "data_sources": "interpark,melon",
    "is_verified": true
  }}
]

규칙:
- confidence: 2개 이상 사이트에서 확인 → 0.8~1.0 / 1개 사이트만 → 0.4~0.6
- is_verified: 2개 이상 사이트에서 교차 확인되면 true
- data_sources: 데이터를 가져온 사이트 이름을 쉼표로 구분
- 원본 데이터에 없는 정보를 지어내지 마세요
- JSON 배열만 출력하세요."""

    def parse_response(self, text: str) -> List[Dict]:
        """AI 응답에서 JSON 추출"""
        text = text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        results = json.loads(text)

        if not isinstance(results, list):
            results = [results]

        return results
