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
    """내한 콘서트 검색 결과 응답"""
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
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True
