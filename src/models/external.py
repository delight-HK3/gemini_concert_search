"""데이터베이스 모델 (MariaDB)

ArtistKeyword → Source DB (키워드 읽기 전용)
CrawledData, ConcertSearchResult → Target DB (결과 저장)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from datetime import datetime
from core.database import SourceBase, TargetBase


class ArtistKeyword(SourceBase):
    """가수 키워드 테이블 (Source DB — 읽기 전용, 이미 존재하는 테이블)"""
    __tablename__ = "artist_keyword"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)


class CrawledData(TargetBase):
    """크롤링 원본 데이터 — Target DB에 저장"""
    __tablename__ = "crawled_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artist_keyword_id = Column(Integer, nullable=False, index=True)
    artist_name = Column(String(500), nullable=False)
    source_site = Column(String(100), nullable=False)
    title = Column(String(500))
    venue = Column(String(500))
    date = Column(String(200))
    time = Column(String(200))
    price = Column(String(500))
    booking_url = Column(Text)
    raw_html = Column(Text)
    crawled_at = Column(DateTime, default=datetime.utcnow)


class ConcertSearchResult(TargetBase):
    """내한 콘서트 검색 결과 — Target DB에 저장 (AI 분석 후 정제된 데이터)"""
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
    confidence = Column(Float, default=0.0)
    data_sources = Column(String(500))
    is_verified = Column(Boolean, default=False)
    synced_at = Column(DateTime, default=datetime.utcnow)
