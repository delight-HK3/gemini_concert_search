"""외부 데이터베이스 모델"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from core.external_database import ExternalBase


class ArtistKeyword(ExternalBase):
    """가수 키워드 테이블 (외부 DB에서 읽기 전용)"""
    __tablename__ = "artist_keyword"

    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)


class ConcertSearchResult(ExternalBase):
    """내한 콘서트 검색 결과 테이블 (외부 DB에 저장)"""
    __tablename__ = "concert_search_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist_keyword_id = Column(Integer, nullable=False)
    artist_name = Column(String(500), nullable=False)
    concert_title = Column(String(500))
    venue = Column(String(500))
    concert_date = Column(String(200))
    concert_time = Column(String(200))
    ticket_price = Column(String(500))
    booking_date = Column(String(200))
    booking_url = Column(Text)
    source = Column(String(200))
    raw_response = Column(Text)
    synced_at = Column(DateTime, default=datetime.utcnow)
