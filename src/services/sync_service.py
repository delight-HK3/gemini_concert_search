"""가수 키워드 동기화 서비스

파이프라인: Source DB 키워드 → 크롤링(여러 사이트) → Target DB 원본 저장 → AI 분석 → Target DB 정제 결과 저장
"""
import asyncio
import json
import logging
from datetime import date, datetime
from sqlalchemy.orm import Session
from models.external import ArtistKeyword, CrawledData, ConcertSearchResult
from crawlers.base import BaseCrawler
from .crawl_service import CrawlService
from .concert_analyzer import ConcertAnalyzer

logger = logging.getLogger(__name__)


class SyncService:
    """크롤링 → AI 분석 → 저장 파이프라인

    source_db: 키워드를 읽어오는 DB 세션
    target_db: 크롤링·분석 결과를 저장하는 DB 세션
    """

    def __init__(self, source_db: Session, target_db: Session):
        self.source_db = source_db
        self.target_db = target_db
        self.crawl_service = CrawlService()
        self.analyzer = ConcertAnalyzer()

    def fetch_artist_keywords(self):
        """Source DB에서 가수 키워드 목록 조회"""
        return self.source_db.query(ArtistKeyword).all()

    def get_already_synced_ids(self):
        """Target DB에서 이미 동기화된 artist_keyword_id 목록"""
        rows = self.target_db.query(ConcertSearchResult.artist_keyword_id).distinct().all()
        return {r[0] for r in rows}

    def _run_async(self, coro):
        """동기 컨텍스트에서 비동기 코루틴 실행"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 이미 이벤트 루프가 실행 중이면 새 스레드에서 실행
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)

    def sync_one(self, artist: ArtistKeyword) -> int:
        """단일 가수: 크롤링 → 원본 저장 → AI 분석 → 정제 결과 저장"""
        logger.info(f"=== 파이프라인 시작: {artist.name} ===")

        # 1단계: 크롤링
        raw_data = self._run_async(self.crawl_service.crawl_all(artist.name))
        logger.info(f"  [크롤링] {len(raw_data)}건 수집")

        # 2단계: 크롤링 원본 저장 (Target DB)
        for item in raw_data:
            record = CrawledData(
                artist_keyword_id=artist.id,
                artist_name=artist.name,
                source_site=item.source_site,
                title=item.title,
                venue=item.venue,
                date=item.date,
                time=item.time,
                price=item.price,
                booking_url=item.booking_url,
                crawled_at=datetime.utcnow(),
            )
            self.target_db.add(record)
        if raw_data:
            self.target_db.commit()
            logger.info(f"  [원본 저장] {len(raw_data)}건")

        # 3단계: AI 분석 (크롤링 데이터가 없으면 AI 폴백 검색)
        analyzed = self.analyzer.analyze(artist.name, raw_data)

        # 크롤링 결과가 있는 경우, AI가 임의로 추가한 ai_search 전용 항목 제거
        if raw_data and analyzed:
            before = len(analyzed)
            analyzed = [
                c for c in analyzed
                if c.get("source") != "ai_search"
                and c.get("data_sources") != "ai_only"
            ]
            if len(analyzed) < before:
                logger.info(f"  [필터] AI 전용 항목 {before - len(analyzed)}건 제거 (크롤링 데이터 존재)")

        # AI 결과에서도 지난 공연 제거 (concert_date 기준)
        if analyzed:
            before = len(analyzed)
            analyzed = [
                c for c in analyzed
                if not BaseCrawler.is_past_event(c.get("concert_date"))
            ]
            if len(analyzed) < before:
                logger.info(f"  [필터] 지난 공연 {before - len(analyzed)}건 제거")
        
        logger.info(f"  [AI 분석] {len(analyzed)}건 정제")

        # 4단계: 정제 결과 저장 (Target DB)
        if not analyzed:
            logger.info(f"  {artist.name}: 결과 없음, 건너뜀")
            return 0

        saved = 0
        for c in analyzed:
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
                source=c.get("source", "crawl+ai"),
                raw_response=json.dumps(c, ensure_ascii=False),
                confidence=c.get("confidence", 0.0),
                data_sources=c.get("data_sources", ""),
                is_verified=c.get("is_verified", False),
                synced_at=datetime.utcnow(),
            )
            self.target_db.add(record)
            saved += 1

        self.target_db.commit()
        logger.info(f"  [저장 완료] {saved}건")
        return saved

    def sync_all(self, force: bool = False) -> dict:
        """전체 동기화. force=True면 이미 동기화된 것도 다시 검색."""
        artists = self.fetch_artist_keywords()
        if not artists:
            logger.info("No artist keywords found in DB")
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
                # force 모드일 때 기존 결과 삭제 (Target DB)
                if force and artist.id in self.get_already_synced_ids():
                    self.target_db.query(ConcertSearchResult).filter(
                        ConcertSearchResult.artist_keyword_id == artist.id
                    ).delete()
                    self.target_db.query(CrawledData).filter(
                        CrawledData.artist_keyword_id == artist.id
                    ).delete()
                    self.target_db.commit()

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

    def sync_by_artist_name(self, artist_name: str, force: bool = False) -> dict:
        """특정 가수 이름으로 동기화. 키워드 테이블에 없으면 None 반환."""
        artist = self.source_db.query(ArtistKeyword).filter(ArtistKeyword.name == artist_name).first()
        if not artist:
            return None

        # 이미 동기화된 경우 처리
        if not force and artist.id in self.get_already_synced_ids():
            return {"artist_name": artist.name, "concerts_found": 0, "skipped": True}

        # force 모드일 때 기존 결과 삭제 (Target DB)
        if force and artist.id in self.get_already_synced_ids():
            self.target_db.query(ConcertSearchResult).filter(
                ConcertSearchResult.artist_keyword_id == artist.id
            ).delete()
            self.target_db.query(CrawledData).filter(
                CrawledData.artist_keyword_id == artist.id
            ).delete()
            self.target_db.commit()

        count = self.sync_one(artist)
        return {"artist_name": artist.name, "concerts_found": count, "skipped": False}

    def get_results(self, artist_name: str = None):
        """검색 결과 조회 (Target DB)"""
        query = self.target_db.query(ConcertSearchResult)
        if artist_name:
            query = query.filter(ConcertSearchResult.artist_name.like(f"%{artist_name}%"))
        return query.order_by(ConcertSearchResult.synced_at.desc()).all()

    def get_results_by_keyword_id(self, artist_keyword_id: int):
        """특정 가수 키워드 ID의 검색 결과 조회 (Target DB)"""
        return (
            self.target_db.query(ConcertSearchResult)
            .filter(ConcertSearchResult.artist_keyword_id == artist_keyword_id)
            .order_by(ConcertSearchResult.synced_at.desc())
            .all()
        )

    def get_crawled_data(self, artist_name: str = None):
        """크롤링 원본 데이터 조회 (Target DB)"""
        query = self.target_db.query(CrawledData)
        if artist_name:
            query = query.filter(CrawledData.artist_name.like(f"%{artist_name}%"))
        return query.order_by(CrawledData.crawled_at.desc()).all()
