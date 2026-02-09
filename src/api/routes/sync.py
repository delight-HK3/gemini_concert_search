"""가수 키워드 동기화 API 라우트"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from core.config import settings
from core.database import get_db
from services.sync_service import SyncService
from api.schemas import SyncResponse, ConcertSearchResultResponse

router = APIRouter()


@router.post("/run", response_model=SyncResponse)
def run_sync(
    force: bool = Query(False, description="이미 동기화된 가수도 다시 검색"),
    db: Session = Depends(get_db),
):
    """가수 키워드 동기화 실행 (MariaDB → Gemini → MariaDB)"""
    if not settings.DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not configured")

    service = SyncService(db)
    result = service.sync_all(force=force)
    return result


@router.get("/results", response_model=List[ConcertSearchResultResponse])
def list_results(
    artist_name: Optional[str] = Query(None, description="가수 이름으로 필터"),
    db: Session = Depends(get_db),
):
    """콘서트 검색 결과 조회"""
    if not settings.DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")

    service = SyncService(db)
    return service.get_results(artist_name=artist_name)


@router.get("/results/{artist_keyword_id}", response_model=List[ConcertSearchResultResponse])
def get_results_by_artist(
    artist_keyword_id: int,
    db: Session = Depends(get_db),
):
    """특정 가수 키워드 ID의 콘서트 검색 결과 조회"""
    if not settings.DATABASE_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not configured")

    service = SyncService(db)
    results = service.get_results_by_keyword_id(artist_keyword_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found for this artist")
    return results
