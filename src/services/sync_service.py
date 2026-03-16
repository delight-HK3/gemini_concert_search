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

    @staticmethod
    def _is_empty(value) -> bool:
        """값이 비어있거나 미정인지 확인"""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() in ("", "미정"):
            return True
        return False

    def _find_existing_record(self, artist_id: int,
                              concert: dict):
        """기존 레코드 중 동일 공연 찾기 (booking_url 우선, 없으면 제목+장소)"""
        booking_url = concert.get("booking_url")

        if booking_url:
            existing = self.target_db.query(ConcertSearchResult).filter(
                ConcertSearchResult.artist_keyword_id == artist_id,
                ConcertSearchResult.booking_url == booking_url,
            ).first()
            if existing:
                return existing

        # 폴백: 제목 + 장소로 매칭
        title = concert.get("concert_title")
        venue = concert.get("venue")
        if title:
            query = self.target_db.query(ConcertSearchResult).filter(
                ConcertSearchResult.artist_keyword_id == artist_id,
                ConcertSearchResult.concert_title == title,
            )
            if venue:
                query = query.filter(ConcertSearchResult.venue == venue)
            existing = query.first()
            if existing:
                return existing

        return None

    def _update_record(self, existing: ConcertSearchResult,
                       new_data: dict) -> bool:
        """기존 레코드의 빈 필드만 새 데이터로 채움. 변경이 있으면 True 반환."""
        updatable_fields = [
            "concert_date", "concert_time", "ticket_price",
            "booking_date", "booking_url",
        ]
        updated = False
        for field in updatable_fields:
            old_value = getattr(existing, field)
            new_value = new_data.get(field)
            if self._is_empty(old_value) and not self._is_empty(new_value):
                setattr(existing, field, new_value)
                updated = True

        if updated:
            existing.synced_at = datetime.utcnow()
            existing.raw_response = json.dumps(new_data, ensure_ascii=False)

        return updated

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

    def sync_one(self, artist: ArtistKeyword, force: bool = False) -> dict:
        """단일 가수: 크롤링 → 원본 저장 → AI 분석 → 정제 결과 저장"""
        logger.info(f"=== 파이프라인 시작: {artist.name} ===")

        # ── 1단계: 크롤링 ──
        raw_data = self._run_async(self.crawl_service.crawl_all(artist.name))
        logger.info(f"  [크롤링] {len(raw_data)}건 수집")

        if raw_data:
            # ── 크롤링 성공 경로 ──
            analyzed = self._process_crawled(artist, raw_data)
        else:
            # ── 크롤링 실패 → AI 검색 폴백 ──
            logger.info(f"  [크롤링 실패] 결과 없음 → AI 검색으로 전환")
            analyzed = self.analyzer.search_concerts(artist.name)
            if analyzed:
                logger.info(f"  [AI 검색] {len(analyzed)}건 발견")
            else:
                logger.info(f"  [AI 검색] 결과 없음")

        # ── 공통: 아티스트 검증 ──
        if analyzed:
            before = len(analyzed)
            analyzed = self.analyzer.verify_artist_match(artist.name, analyzed)
            if len(analyzed) < before:
                logger.info(f"  [아티스트 검증] {before - len(analyzed)}건 제거됨")

        # ── 공통: 지난 공연 제거 ──
        if analyzed:
            before = len(analyzed)
            analyzed = [
                c for c in analyzed
                if not BaseCrawler.is_past_event(c.get("concert_date"))
            ]
            if len(analyzed) < before:
                logger.info(f"  [필터] 지난 공연 {before - len(analyzed)}건 제거")

        logger.info(f"  [최종] {len(analyzed)}건 정제")

        # ── 결과 저장 ──
        if not analyzed:
            logger.info(f"  {artist.name}: 결과 없음, 건너뜀")
            return {"inserted": 0, "updated": 0, "skipped": 0}

        return self._save_results(artist, analyzed, force=force)

    def _process_crawled(self, artist: ArtistKeyword,
                         raw_data: list) -> list:
        """크롤링 성공: 원본 저장 → AI 분석 → 필터"""
        # 크롤링 원본 저장
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
        self.target_db.commit()
        logger.info(f"  [원본 저장] {len(raw_data)}건")

        # AI 분석 (크롤링 데이터 기반)
        analyzed = self.analyzer.analyze(artist.name, raw_data)

        # AI가 임의로 추가한 ai_search 전용 항목 제거
        if analyzed:
            before = len(analyzed)
            analyzed = [
                c for c in analyzed
                if c.get("source") != "ai_search"
                and c.get("data_sources") != "ai_only"
            ]
            if len(analyzed) < before:
                logger.info(f"  [필터] AI 전용 항목 {before - len(analyzed)}건 제거")

        return analyzed

    def _save_results(self, artist: ArtistKeyword,
                      analyzed: list, force: bool = False) -> dict:
        """정제된 결과를 ConcertSearchResult 테이블에 저장 (upsert 지원)

        force=False: 기존 레코드 매칭 → 빈 필드만 갱신, 새 공연은 신규 삽입
        force=True: 전부 신규 삽입 (기존 데이터는 이미 삭제된 상태)
        """
        inserted = 0
        updated = 0
        skipped = 0

        for c in analyzed:
            if not force:
                existing = self._find_existing_record(artist.id, c)
                if existing:
                    if self._update_record(existing, c):
                        updated += 1
                    else:
                        skipped += 1
                    continue

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
            inserted += 1

        self.target_db.commit()
        logger.info(
            f"  [저장 완료] 신규 {inserted}건, 업데이트 {updated}건, 변경없음 {skipped}건"
        )
        return {"inserted": inserted, "updated": updated, "skipped": skipped}

    def sync_all(self, force: bool = False) -> dict:
        """전체 동기화.

        force=False: 모든 아티스트 파이프라인 실행, 기존 레코드의 빈 필드만 갱신 + 새 공연 삽입
        force=True: 기존 데이터 전부 삭제 후 재삽입
        """
        artists = self.fetch_artist_keywords()
        if not artists:
            logger.info("No artist keywords found in DB")
            return {
                "total_artists": 0, "synced": 0, "skipped": 0,
                "concerts_found": 0, "concerts_updated": 0,
            }

        total = len(artists)
        synced = 0
        concerts_found = 0
        concerts_updated = 0

        for artist in artists:
            if force:
                # force 모드: 기존 결과 삭제 후 재삽입
                self.target_db.query(ConcertSearchResult).filter(
                    ConcertSearchResult.artist_keyword_id == artist.id
                ).delete()
                self.target_db.query(CrawledData).filter(
                    CrawledData.artist_keyword_id == artist.id
                ).delete()
                self.target_db.commit()

            save_result = self.sync_one(artist, force=force)
            synced += 1
            concerts_found += save_result["inserted"]
            concerts_updated += save_result["updated"]

        result = {
            "total_artists": total,
            "synced": synced,
            "skipped": 0,
            "concerts_found": concerts_found,
            "concerts_updated": concerts_updated,
        }
        logger.info(f"Sync complete: {result}")
        return result

    def sync_by_artist_name(self, artist_name: str, force: bool = False) -> dict:
        """특정 가수 이름으로 동기화. 키워드 테이블에 없으면 None 반환."""
        artist = self.source_db.query(ArtistKeyword).filter(ArtistKeyword.name == artist_name).first()
        if not artist:
            return None

        # force 모드일 때 기존 결과 삭제 (Target DB)
        if force:
            self.target_db.query(ConcertSearchResult).filter(
                ConcertSearchResult.artist_keyword_id == artist.id
            ).delete()
            self.target_db.query(CrawledData).filter(
                CrawledData.artist_keyword_id == artist.id
            ).delete()
            self.target_db.commit()

        save_result = self.sync_one(artist, force=force)
        return {
            "artist_name": artist.name,
            "concerts_found": save_result["inserted"],
            "concerts_updated": save_result["updated"],
            "skipped": False,
        }

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
