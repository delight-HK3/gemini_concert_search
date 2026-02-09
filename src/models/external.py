"""데이터베이스 모델 (MariaDB)"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from core.database import Base


class ArtistKeyword(Base):
    """가수 키워드 테이블 (읽기 전용 — 이미 존재하는 테이블)"""
    __tablename__ = "artist_keyword"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)


class ConcertSearchResult(Base):
    """내한 콘서트 검색 결과 테이블 (자동 생성)"""
    __tablename__ = "concert_search_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist_keyword_id = Column(Integer, nullable=False, index=True)
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
