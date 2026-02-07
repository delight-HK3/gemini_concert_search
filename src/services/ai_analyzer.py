"""AI 분석 서비스"""
import google.generativeai as genai
import json
import logging
from typing import Dict
from core.config import settings

logger = logging.getLogger(__name__)

class KeywordAnalyzer:
    """Gemini AI를 사용한 키워드 분석기"""
    
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not set. AI features disabled.")
            self.model = None
            return
        
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(settings.AI_MODEL)
    
    def analyze(self, keyword: str) -> Dict:
        """키워드 분석"""
        if not self.model:
            return self._default_result(keyword)
        
        try:
            prompt = f"""다음 키워드를 분석하세요: "{keyword}"

다음 정보를 JSON 형식으로 제공하세요:
1. summary: 간단한 요약
2. category: 카테고리 (엔터테인먼트, 기술, 스포츠 등)
3. is_artist: 가수/아티스트 여부 (true/false)
4. artist_names: 아티스트 이름 목록 (여러 이름 포함, 예: ["아이유", "IU"])
5. genre: 음악 장르 (아티스트인 경우)
6. confidence: 신뢰도 (0.0~1.0)

JSON만 출력하세요."""

            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # JSON 추출
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(text)
            logger.info(f"AI analysis complete: {keyword}")
            return result
            
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self._default_result(keyword)
    
    def _default_result(self, keyword: str) -> Dict:
        """기본 결과 (AI 사용 불가 시)"""
        return {
            "summary": f"'{keyword}' 키워드",
            "category": "미분류",
            "is_artist": False,
            "artist_names": [],
            "genre": None,
            "confidence": 0.0
        }
