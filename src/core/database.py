"""MariaDB 데이터베이스 연결 및 세션 관리"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_SessionLocal = None


def _get_engine():
    """DB 엔진 (lazy init)"""
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not configured")
        url = settings.DATABASE_URL
        # jdbc:mysql:// → mysql+pymysql://
        if url.startswith("jdbc:"):
            url = url[len("jdbc:"):]
        # mysql:// → mysql+pymysql://
        if url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+pymysql://", 1)
        # mariadb:// → mariadb+pymysql://
        elif url.startswith("mariadb://"):
            url = url.replace("mariadb://", "mariadb+pymysql://", 1)
        logger.info(f"Connecting to database (scheme: {url.split('://')[0]})")
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_session_factory():
    """DB 세션 팩토리"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine())
    return _SessionLocal


def get_db():
    """DB 세션 의존성 (FastAPI Depends용)"""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """DB 초기화 — concert_search_results 테이블 자동 생성"""
    if not settings.DATABASE_URL:
        logger.warning("DATABASE_URL not set — skipping DB init")
        return
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("✓ Database tables initialized")
