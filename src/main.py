"""FastAPI 메인 애플리케이션"""
from fastapi import FastAPI
import logging
from core import init_db, settings
from services import start_scheduler
from api.routes import keywords, health

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="AI Keyword Processor",
    description="Gemini AI를 활용한 키워드 분석 시스템",
    version="3.0.0"
)

@app.on_event("startup")
def startup_event():
    """애플리케이션 시작"""
    logger.info("=== Starting AI Keyword Processor ===")
    
    # DB 초기화
    init_db()
    logger.info("✓ Database initialized")
    
    # 스케줄러 시작
    start_scheduler()

@app.get("/")
def root():
    """루트 엔드포인트"""
    return {
        "service": "AI Keyword Processor",
        "version": "3.0.0",
        "ai_enabled": bool(settings.GOOGLE_API_KEY),
        "scheduler_enabled": settings.ENABLE_SCHEDULER
    }

# 라우터 등록
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(keywords.router, prefix="/keywords", tags=["Keywords"])
