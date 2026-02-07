"""키워드 비즈니스 로직"""
from sqlalchemy.orm import Session
from models import Keyword, ProcessedResult, Concert
from .ai_analyzer import KeywordAnalyzer
import logging

logger = logging.getLogger(__name__)

class KeywordService:
    """키워드 처리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.analyzer = KeywordAnalyzer()
    
    def create_keyword(self, text: str) -> Keyword:
        """키워드 생성"""
        keyword = Keyword(text=text)
        self.db.add(keyword)
        self.db.commit()
        self.db.refresh(keyword)
        return keyword
    
    def get_keyword(self, keyword_id: int) -> Keyword:
        """키워드 조회"""
        return self.db.query(Keyword).filter(Keyword.id == keyword_id).first()
    
    def list_keywords(self, limit: int = 100):
        """키워드 목록"""
        return self.db.query(Keyword).order_by(Keyword.created_at.desc()).limit(limit).all()
    
    def process_keyword(self, keyword_id: int) -> dict:
        """키워드 AI 분석 및 처리"""
        keyword = self.get_keyword(keyword_id)
        if not keyword:
            raise ValueError("Keyword not found")
        
        if keyword.processed:
            return {"message": "Already processed"}
        
        # AI 분석
        analysis = self.analyzer.analyze(keyword.text)
        
        # 결과 저장
        result = ProcessedResult(
            keyword_id=keyword.id,
            summary=analysis.get('summary', ''),
            category=analysis.get('category', '미분류'),
            is_artist=analysis.get('is_artist', False),
            artist_names=analysis.get('artist_names', []),
            genre=analysis.get('genre'),
            confidence=analysis.get('confidence', 0.0)
        )
        self.db.add(result)
        self.db.flush()
        
        # 아티스트면 콘서트 정보 추가 (예시)
        if result.is_artist:
            concert = Concert(
                result_id=result.id,
                title=f"{keyword.text} 콘서트 2026",
                artist=keyword.text,
                date="2026-03-15",
                venue="예시 공연장",
                city="서울",
                source="예시"
            )
            self.db.add(concert)
        
        keyword.processed = True
        self.db.commit()
        
        logger.info(f"Processed keyword: {keyword.text}")
        
        return {
            "message": "Processed successfully",
            "is_artist": result.is_artist,
            "artist_names": result.artist_names
        }
    
    def get_result(self, keyword_id: int) -> ProcessedResult:
        """분석 결과 조회"""
        return self.db.query(ProcessedResult).filter(
            ProcessedResult.keyword_id == keyword_id
        ).first()
