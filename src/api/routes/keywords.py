"""키워드 API 라우트"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from services import KeywordService
from api.schemas import KeywordCreate, KeywordResponse, ResultResponse

router = APIRouter()

@router.post("/", response_model=KeywordResponse)
def create_keyword(keyword: KeywordCreate, db: Session = Depends(get_db)):
    """키워드 생성"""
    service = KeywordService(db)
    result = service.create_keyword(keyword.text)
    return result

@router.get("/", response_model=List[KeywordResponse])
def list_keywords(db: Session = Depends(get_db)):
    """키워드 목록"""
    service = KeywordService(db)
    return service.list_keywords()

@router.get("/{keyword_id}", response_model=KeywordResponse)
def get_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """키워드 조회"""
    service = KeywordService(db)
    keyword = service.get_keyword(keyword_id)
    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return keyword

@router.post("/{keyword_id}/process")
def process_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """키워드 처리"""
    service = KeywordService(db)
    try:
        return service.process_keyword(keyword_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{keyword_id}/result", response_model=ResultResponse)
def get_result(keyword_id: int, db: Session = Depends(get_db)):
    """분석 결과 조회"""
    service = KeywordService(db)
    result = service.get_result(keyword_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result
