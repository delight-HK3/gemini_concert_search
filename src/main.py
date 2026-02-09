"""FastAPI 메인 애플리케이션"""
from fastapi import FastAPI
import logging
from core import init_db, settings
from services import start_scheduler
from api.routes import health, sync

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="Singer Concert Search",
    description="MariaDB 가수 키워드 기반 Gemini 내한 콘서트 검색 시스템",
    version="5.0.0"
)

@app.on_event("startup")
def startup_event():
    """애플리케이션 시작"""
    logger.info("=== Starting Singer Concert Search ===")

    # DB 초기화 (concert_search_results 테이블 생성)
    init_db()

    # 스케줄러 시작
    start_scheduler()

@app.get("/")
def root():
    """루트 엔드포인트"""
    return {
        "service": "Singer Concert Search",
        "version": "5.0.0",
        "ai_enabled": bool(settings.GOOGLE_API_KEY),
        "db_configured": bool(settings.DATABASE_URL),
        "scheduler_enabled": settings.ENABLE_SCHEDULER,
    }

# 라우터 등록
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(sync.router, prefix="/sync", tags=["Singer Sync"])
