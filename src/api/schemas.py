"""Pydantic 스키마"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SyncResponse(BaseModel):
    """동기화 실행 결과"""
    total_artists: int
    synced: int
    skipped: int
    concerts_found: int


class ConcertSearchResultResponse(BaseModel):
    """내한 콘서트 검색 결과 응답 (AI 분석 후 정제 데이터)"""
    id: int
    artist_keyword_id: int
    artist_name: str
    concert_title: Optional[str]
    venue: Optional[str]
    concert_date: Optional[str]
    concert_time: Optional[str]
    ticket_price: Optional[str]
    booking_date: Optional[str]
    booking_url: Optional[str]
    source: Optional[str]
    confidence: Optional[float]
    data_sources: Optional[str]
    is_verified: Optional[bool]
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class CrawledDataResponse(BaseModel):
    """크롤링 원본 데이터 응답"""
    id: int
    artist_keyword_id: int
    artist_name: str
    source_site: str
    title: Optional[str]
    venue: Optional[str]
    date: Optional[str]
    time: Optional[str]
    price: Optional[str]
    booking_url: Optional[str]
    crawled_at: Optional[datetime]

    class Config:
        from_attributes = True
