"""AI 콘서트 데이터 분석 서비스

크롤링된 원본 데이터를 Gemini AI로 분석·정제·보강한다.
역할: 데이터 정제, 중복 판별, 정보 보강, 빠진 세부정보 검색 보충
"""
from google import genai
from google.genai import types
import json
import logging
import time
import re
from datetime import date
from typing import List, Dict
from core.config import settings
from crawlers.base import RawConcertData

logger = logging.getLogger(__name__)

# Google Search 도구 — 크롤링에서 빠진 정보를 AI가 웹 검색으로 보충
_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())


class ConcertAnalyzer:
    """Gemini AI를 사용한 크롤링 데이터 분석기"""

    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not set. AI analysis disabled.")
            self.client = None
            return

        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    def _generate_with_retry(self, prompt: str, max_retries: int = 3,
                             use_search: bool = False) -> str:
        """Gemini API 호출 (429 rate limit 시 자동 재시도)

        Args:
            use_search: True이면 Google Search grounding을 활성화하여
                        크롤링에 없는 정보를 웹에서 검색·보충한다.
        """
        config = None
        if use_search:
            config = types.GenerateContentConfig(tools=[_SEARCH_TOOL])

        for attempt in range(max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=settings.AI_MODEL,
                    contents=prompt,
                    config=config,
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries:
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

        크롤링 결과는 '콘서트가 실제로 존재한다는 증거'로 취급한다.
        빠진 세부정보(공연시간, 티켓가격, 예매시작일)는 AI가 검색으로 보충한다.

        Args:
            artist_name: 아티스트 이름
            raw_data: 여러 사이트에서 크롤링한 원본 데이터

        Returns:
            정제된 콘서트 정보 목록 (중복 제거, 빠진 정보 보충 포함)
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

            # Google Search grounding 활성화 — 빠진 정보 웹 검색 보충
            text = self._generate_with_retry(prompt, use_search=True)
            results = self.parse_response(text)

            # 크롤링 데이터보다 AI 결과가 많으면 초과분 제거 (AI가 임의 추가한 항목)
            if len(results) > len(raw_data):
                logger.warning(
                    f"AI 결과({len(results)}건)가 크롤링 데이터({len(raw_data)}건)보다 많음 — 초과분 제거"
                )
                # 크롤링 booking_url 기반으로 매칭된 항목만 유지
                crawled_urls = {d.booking_url for d in raw_data if d.booking_url}
                matched = [r for r in results if r.get("booking_url") in crawled_urls]
                results = matched if matched else results[:len(raw_data)]

            return results

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
- ticket_price: 티켓 가격 정보. 금액 단위는 '원'. 가격대가 하나면 "전석 99,000원", 여러 등급이면 "VIP 198,000원 / R석 165,000원" 형식. 지정석과 스탠딩석 가격이 동일해도 "지정석 111,000원 / 스탠딩석 111,000원"처럼 각각 표기
- booking_date: 예매 시작일 (예: "2026-02-01")
- booking_url: 예매 링크
- source: "ai_search"
- confidence: 0.3
- data_sources: "ai_only"
- is_verified: false

오늘 날짜 이전에 이미 종료된 공연은 제외하세요 (오늘: {date.today().isoformat()}).
확인된 정보가 없으면 빈 배열 []을 반환하세요.
추측이나 가짜 정보는 절대 포함하지 마세요.
JSON 배열만 출력하세요."""

            text = self._generate_with_retry(prompt, use_search=True)
            return self.parse_response(text)

        except Exception as e:
            logger.error(f"AI 폴백 검색 오류 '{artist_name}': {e}")
            return []

    def build_analysis_prompt(self, artist_name: str, crawled_json: str) -> str:
        """AI 분석 프롬프트 생성"""
        return f"""다음은 여러 티켓 사이트에서 크롤링한 "{artist_name}"의 콘서트 원본 데이터입니다.
크롤링 데이터는 해당 콘서트가 실제로 존재한다는 증거입니다.

{crawled_json}

위 데이터를 분석하여 다음 작업을 수행하세요:

1. **사이트별 개별 유지**: 같은 공연이라도 사이트별로 별도 항목으로 유지하세요 (병합 금지). 각 사이트의 booking_url이 다르므로 반드시 개별 저장해야 합니다.
2. **데이터 정제**: 날짜(YYYY-MM-DD), 시간(HH:MM), 가격 형식을 통일
3. **교차 검증**: 같은 공연이 여러 사이트에 있으면 is_verified를 true로 설정
4. **빠진 정보 검색 보충**: 크롤링 데이터에 아래 항목이 비어있으면(null) 웹 검색을 통해 찾아서 채워주세요:
   - **concert_time** (공연 시간): 크롤링 결과에 time이 null인 경우 검색으로 보충
   - **ticket_price** (티켓 가격): 크롤링 결과에 price가 null인 경우 좌석 등급별 가격을 검색으로 보충
   - **booking_date** (예매 시작일): 티켓 오픈일/예매 시작일을 검색으로 보충

결과를 다음 JSON 배열 형식으로 출력하세요 (크롤링 항목 수와 동일한 수의 항목):
[
  {{
    "concert_title": "크롤링 데이터의 title 필드 값을 그대로 사용",
    "venue": "공연 장소",
    "concert_date": "2026-03-15",
    "concert_time": "19:00",
    "ticket_price": "VIP 198,000원 / R석 165,000원 / S석 132,000원",
    "booking_date": "2026-02-01",
    "booking_url": "https://tickets.interpark.com/...",
    "source": "crawl+ai",
    "confidence": 0.85,
    "data_sources": "interpark",
    "is_verified": true
  }},
  {{
    "concert_title": "크롤링 데이터의 title 필드 값을 그대로 사용",
    "venue": "공연 장소",
    "concert_date": "2026-03-15",
    "concert_time": "19:00",
    "ticket_price": "VIP 198,000원 / R석 165,000원 / S석 132,000원",
    "booking_date": "2026-02-01",
    "booking_url": "https://ticket.yes24.com/...",
    "source": "crawl+ai",
    "confidence": 0.85,
    "data_sources": "yes24",
    "is_verified": true
  }}
]

규칙:
- **절대 규칙**: 크롤링 데이터에 있는 공연만 결과에 포함하세요. 크롤링 데이터에 없는 공연을 임의로 추가하거나 만들어내지 마세요. 결과 항목 수는 크롤링 데이터의 항목 수와 정확히 같아야 합니다.
- **concert_title**: 각 크롤링 항목의 "title" 필드 값을 그대로 사용하세요 (아티스트 이름이 아닌 실제 공연 제목).
- 같은 공연이라도 사이트별로 별도 항목을 유지하세요 (각 사이트의 booking_url을 보존)
- 크롤링 데이터에 이미 있는 정보(제목, 장소, 날짜 등)는 그대로 사용하세요
- concert_time, ticket_price, booking_date가 크롤링에 없을 때만 검색으로 보충하세요
- ticket_price 포맷: 금액 단위는 반드시 '원'을 사용하세요 (예: 99,000원). 가격대가 하나뿐이면 앞에 "전석"을 붙이세요 (예: "전석 99,000원"). 여러 등급이면 "VIP 198,000원 / R석 165,000원" 형식으로 작성하세요. 지정석과 스탠딩석 가격이 동일하더라도 "전석"으로 합치지 말고 "스탠딩석 111,000원 / 지정석 111,000원"처럼 각각 분리하여 표기하세요
- 검색으로 보충한 필드가 있으면 source에 "crawl+ai_search"로 표기하세요
- 검색으로도 찾을 수 없는 정보는 null로 두세요 (추측하지 마세요)
- confidence: 여러 사이트에서 교차 확인된 공연 → 0.8~1.0 / 1개 사이트만 → 0.5~0.7 / AI 보충 포함 → 0.4~0.6
- is_verified: 같은 공연이 2개 이상 사이트에서 확인되면 true (각 항목 모두 true)
- data_sources: 해당 항목의 원본 사이트 이름 (AI 보충 시 "사이트명,ai_search")
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
