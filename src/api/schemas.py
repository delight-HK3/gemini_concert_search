"""Pydantic 스키마"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class KeywordCreate(BaseModel):
    """키워드 생성 요청"""
    text: str

class KeywordResponse(BaseModel):
    """키워드 응답"""
    id: int
    text: str
    processed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConcertResponse(BaseModel):
    """콘서트 정보 응답"""
    id: int
    title: str
    artist: str
    date: Optional[str]
    venue: str
    city: Optional[str]
    source: str
    
    class Config:
        from_attributes = True

class ResultResponse(BaseModel):
    """분석 결과 응답"""
    id: int
    summary: str
    category: str
    is_artist: bool
    artist_names: Optional[List[str]]
    genre: Optional[str]
    confidence: float
    concerts: List[ConcertResponse] = []

    class Config:
        from_attributes = True


# === 가수 키워드 동기화 관련 스키마 ===

class SyncResponse(BaseModel):
    """동기화 실행 결과"""
    total_artists: int
    synced: int
    skipped: int
    concerts_found: int


class SyncResultResponse(BaseModel):
    """동기화 결과 요약"""
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
