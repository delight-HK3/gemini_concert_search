"""데이터베이스 연결 및 세션 관리"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# SQLAlchemy 엔진
engine = create_engine(
    settings.DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')
)

# 세션 팩토리
SessionLocal = sessionmaker(bind=engine)

# Base 클래스
Base = declarative_base()

def get_db():
    """DB 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """DB 초기화"""
    Base.metadata.create_all(bind=engine)
