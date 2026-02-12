"""데이터베이스 연결 및 세션 관리

Source DB: 가수 키워드를 읽어오는 DB (읽기 전용)
Target DB: 크롤링 원본·AI 분석 결과를 저장하는 DB
SQLAlchemy 지원 DB 모두 사용 가능 (MySQL, MariaDB, PostgreSQL, SQLite 등)
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

logger = logging.getLogger(__name__)

SourceBase = declarative_base()
TargetBase = declarative_base()

_source_engine = None
_target_engine = None
_SourceSessionLocal = None
_TargetSessionLocal = None


def _normalize_url(url: str) -> str:
    """DB 연결 문자열 정규화 — SQLAlchemy가 인식할 수 있는 형태로 변환"""
    # JDBC prefix 제거
    if url.startswith("jdbc:"):
        url = url[len("jdbc:"):]
    # scheme에 드라이버가 없으면 기본 드라이버 추가
    scheme = url.split("://")[0] if "://" in url else ""
    if "+" not in scheme:
        driver_map = {
            "mysql": "mysql+pymysql",
            "mariadb": "mariadb+pymysql",
            "postgresql": "postgresql+psycopg2",
            "postgres": "postgresql+psycopg2",
        }
        if scheme in driver_map:
            url = url.replace(f"{scheme}://", f"{driver_map[scheme]}://", 1)
    return url


def _get_source_engine():
    """Source DB 엔진 (lazy init) — 키워드 읽기용"""
    global _source_engine
    if _source_engine is None:
        url = settings.source_db_url
        if not url:
            raise RuntimeError("SOURCE_DATABASE_URL (또는 DATABASE_URL)이 설정되지 않았습니다")
        url = _normalize_url(url)
        logger.info(f"Connecting to SOURCE DB (scheme: {url.split('://')[0]})")
        _source_engine = create_engine(url, pool_pre_ping=True)
    return _source_engine


def _get_target_engine():
    """Target DB 엔진 (lazy init) — 결과 저장용"""
    global _target_engine
    if _target_engine is None:
        url = settings.target_db_url
        if not url:
            raise RuntimeError("TARGET_DATABASE_URL (또는 DATABASE_URL)이 설정되지 않았습니다")
        url = _normalize_url(url)
        logger.info(f"Connecting to TARGET DB (scheme: {url.split('://')[0]})")
        _target_engine = create_engine(url, pool_pre_ping=True)
    return _target_engine


def get_source_session_factory():
    """Source DB 세션 팩토리"""
    global _SourceSessionLocal
    if _SourceSessionLocal is None:
        _SourceSessionLocal = sessionmaker(bind=_get_source_engine())
    return _SourceSessionLocal


def get_target_session_factory():
    """Target DB 세션 팩토리"""
    global _TargetSessionLocal
    if _TargetSessionLocal is None:
        _TargetSessionLocal = sessionmaker(bind=_get_target_engine())
    return _TargetSessionLocal


def get_source_db():
    """Source DB 세션 의존성 (FastAPI Depends용)"""
    factory = get_source_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def get_target_db():
    """Target DB 세션 의존성 (FastAPI Depends용)"""
    factory = get_target_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """DB 초기화 — Target DB에 테이블 자동 생성"""
    if not settings.target_db_url:
        logger.warning("TARGET_DATABASE_URL not set — skipping DB init")
        return
    engine = _get_target_engine()
    TargetBase.metadata.create_all(bind=engine)
    logger.info("✓ Target database tables initialized")
