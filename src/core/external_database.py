"""외부 데이터베이스 연결 및 세션 관리"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

logger = logging.getLogger(__name__)

ExternalBase = declarative_base()

_external_engine = None
_ExternalSessionLocal = None


def _get_engine():
    """외부 DB 엔진 (lazy init)"""
    global _external_engine
    if _external_engine is None:
        if not settings.EXTERNAL_DATABASE_URL:
            raise RuntimeError("EXTERNAL_DATABASE_URL is not configured")
        url = settings.EXTERNAL_DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        _external_engine = create_engine(url)
    return _external_engine


def get_external_session_factory():
    """외부 DB 세션 팩토리"""
    global _ExternalSessionLocal
    if _ExternalSessionLocal is None:
        _ExternalSessionLocal = sessionmaker(bind=_get_engine())
    return _ExternalSessionLocal


def get_external_db():
    """외부 DB 세션 의존성 (FastAPI Depends용)"""
    factory = get_external_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_external_db():
    """외부 DB에 결과 테이블 생성"""
    if not settings.EXTERNAL_DATABASE_URL:
        logger.warning("EXTERNAL_DATABASE_URL not set — skipping external DB init")
        return
    engine = _get_engine()
    ExternalBase.metadata.create_all(bind=engine)
    logger.info("✓ External database tables initialized")
