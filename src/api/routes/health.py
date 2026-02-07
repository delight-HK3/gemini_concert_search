"""헬스체크 라우트"""
from fastapi import APIRouter
from core.config import settings

router = APIRouter()

@router.get("/")
def health_check():
    """헬스체크"""
    return {
        "status": "healthy",
        "ai_enabled": bool(settings.GOOGLE_API_KEY)
    }
