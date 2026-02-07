"""키워드 데이터베이스 모델"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class Keyword(Base):
    """키워드 테이블"""
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(500), nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    result = relationship("ProcessedResult", back_populates="keyword", uselist=False)
