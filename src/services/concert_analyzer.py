"""내한 콘서트 검색 AI 서비스"""
import google.generativeai as genai
import json
import logging
from typing import List, Dict
from core.config import settings

logger = logging.getLogger(__name__)


class ConcertAnalyzer:
    """Gemini AI를 사용한 내한 콘서트 검색기"""

    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not set. Concert search disabled.")
            self.model = None
            return

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(settings.AI_MODEL)

    def search_concerts(self, artist_name: str) -> List[Dict]:
        """가수 이름으로 내한 콘서트 정보 검색"""
        if not self.model:
            return []

        try:
            prompt = f""""{artist_name}"의 한국 내한 콘서트(공연) 정보를 검색해서 알려주세요.

다음 정보를 JSON 배열 형식으로 제공하세요:
- concert_title: 콘서트/공연 제목
- venue: 공연 장소 (예: 고척스카이돔, KSPO DOME 등)
- concert_date: 공연 날짜 (예: "2026-03-15", 여러 날이면 "2026-03-15 ~ 2026-03-17")
- concert_time: 공연 시간 (예: "19:00", "토 17:00 / 일 15:00")
- ticket_price: 티켓 가격 (예: "VIP 198,000원 / R석 165,000원 / S석 132,000원")
- booking_date: 예매 시작일 (예: "2026-02-01 12:00")
- booking_url: 예매 링크 (인터파크, 멜론티켓, YES24 등 실제 예매 사이트 URL)
- source: 정보 출처

알려진 내한 공연 정보가 있으면 모두 포함하세요.
확인된 정보가 없으면 빈 배열 []을 반환하세요.
추측이나 가짜 정보는 절대 포함하지 마세요. 확실한 정보만 제공하세요.

JSON 배열만 출력하세요."""

            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # JSON 추출
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            results = json.loads(text)

            if not isinstance(results, list):
                results = [results]

            logger.info(f"Concert search complete: {artist_name} → {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Concert search error for '{artist_name}': {e}")
            return []
