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
