"""분석 결과 데이터베이스 모델"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class ProcessedResult(Base):
    """AI 분석 결과 테이블"""
    __tablename__ = "processed_results"
    
    id = Column(Integer, primary_key=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), unique=True)
    summary = Column(Text)
    category = Column(String(100))
    is_artist = Column(Boolean, default=False)
    artist_names = Column(JSON)
    genre = Column(String(200))
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    keyword = relationship("Keyword", back_populates="result")
    concerts = relationship("Concert", back_populates="result")

class Concert(Base):
    """콘서트 정보 테이블"""
    __tablename__ = "concerts"
    
    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey("processed_results.id"))
    title = Column(String(500))
    artist = Column(String(200))
    date = Column(String(50))
    venue = Column(String(300))
    city = Column(String(100))
    source = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    result = relationship("ProcessedResult", back_populates="concerts")
