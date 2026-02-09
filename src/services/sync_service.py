"""가수 키워드 동기화 서비스

외부 DB에서 가수 키워드를 가져와 Gemini로 내한 콘서트 정보를 검색하고
결과를 외부 DB에 저장한다.
"""
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from models.external import ArtistKeyword, ConcertSearchResult
from .concert_analyzer import ConcertAnalyzer

logger = logging.getLogger(__name__)


class SyncService:
    """가수 키워드 → Gemini 검색 → 결과 저장"""

    def __init__(self, external_db: Session):
        self.db = external_db
        self.analyzer = ConcertAnalyzer()

    def fetch_artist_keywords(self):
        """외부 DB에서 가수 키워드 목록 조회"""
        return self.db.query(ArtistKeyword).all()

    def get_already_synced_ids(self):
        """이미 동기화된 artist_keyword_id 목록"""
        rows = self.db.query(ConcertSearchResult.artist_keyword_id).distinct().all()
        return {r[0] for r in rows}

    def sync_one(self, artist: ArtistKeyword) -> int:
        """단일 가수 키워드에 대해 콘서트 검색 → 저장. 저장된 건수 반환."""
        logger.info(f"Searching concerts for: {artist.name}")
        concerts = self.analyzer.search_concerts(artist.name)

        if not concerts:
            # 검색 결과 없음 — 빈 레코드 하나를 남겨 중복 검색 방지
            record = ConcertSearchResult(
                artist_keyword_id=artist.id,
                artist_name=artist.name,
                concert_title=None,
                venue=None,
                concert_date=None,
                concert_time=None,
                ticket_price=None,
                booking_date=None,
                booking_url=None,
                source="gemini",
                raw_response="[]",
                synced_at=datetime.utcnow(),
            )
            self.db.add(record)
            self.db.commit()
            logger.info(f"  No concerts found for {artist.name}")
            return 0

        saved = 0
        for c in concerts:
            record = ConcertSearchResult(
                artist_keyword_id=artist.id,
                artist_name=artist.name,
                concert_title=c.get("concert_title"),
                venue=c.get("venue"),
                concert_date=c.get("concert_date"),
                concert_time=c.get("concert_time"),
                ticket_price=c.get("ticket_price"),
                booking_date=c.get("booking_date"),
                booking_url=c.get("booking_url"),
                source=c.get("source", "gemini"),
                raw_response=json.dumps(c, ensure_ascii=False),
                synced_at=datetime.utcnow(),
            )
            self.db.add(record)
            saved += 1

        self.db.commit()
        logger.info(f"  Saved {saved} concerts for {artist.name}")
        return saved

    def sync_all(self, force: bool = False) -> dict:
        """전체 동기화. force=True면 이미 동기화된 것도 다시 검색."""
        artists = self.fetch_artist_keywords()
        if not artists:
            logger.info("No artist keywords found in external DB")
            return {"total_artists": 0, "synced": 0, "skipped": 0, "concerts_found": 0}

        synced_ids = set() if force else self.get_already_synced_ids()

        total = len(artists)
        synced = 0
        skipped = 0
        concerts_found = 0

        for artist in artists:
            if not force and artist.id in synced_ids:
                skipped += 1
                continue
            else:
                # force 모드일 때 기존 결과 삭제
                if force and artist.id in self.get_already_synced_ids():
                    self.db.query(ConcertSearchResult).filter(
                        ConcertSearchResult.artist_keyword_id == artist.id
                    ).delete()
                    self.db.commit()

            count = self.sync_one(artist)
            synced += 1
            concerts_found += count

        result = {
            "total_artists": total,
            "synced": synced,
            "skipped": skipped,
            "concerts_found": concerts_found,
        }
        logger.info(f"Sync complete: {result}")
        return result

    def get_results(self, artist_name: str = None):
        """검색 결과 조회"""
        query = self.db.query(ConcertSearchResult)
        if artist_name:
            query = query.filter(ConcertSearchResult.artist_name.ilike(f"%{artist_name}%"))
        return query.order_by(ConcertSearchResult.synced_at.desc()).all()

    def get_results_by_keyword_id(self, artist_keyword_id: int):
        """특정 가수 키워드 ID의 검색 결과 조회"""
        return (
            self.db.query(ConcertSearchResult)
            .filter(ConcertSearchResult.artist_keyword_id == artist_keyword_id)
            .order_by(ConcertSearchResult.synced_at.desc())
            .all()
        )
