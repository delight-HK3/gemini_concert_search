"""백그라운드 스케줄러"""
import schedule
import time
import logging
from threading import Thread
from core.database import SessionLocal
from core.config import settings
from models import Keyword
from .keyword_service import KeywordService

logger = logging.getLogger(__name__)


def process_batch():
    """배치 처리 작업"""
    logger.info("=== Starting scheduled processing ===")

    db = SessionLocal()
    service = KeywordService(db)

    try:
        keywords = db.query(Keyword).filter(
            Keyword.processed == False
        ).limit(settings.BATCH_SIZE).all()

        if not keywords:
            logger.info("No unprocessed keywords")
            return

        logger.info(f"Processing {len(keywords)} keywords")

        for keyword in keywords:
            try:
                service.process_keyword(keyword.id)
                logger.info(f"✓ Processed: {keyword.text}")
            except Exception as e:
                logger.error(f"✗ Error processing {keyword.text}: {e}")

    finally:
        db.close()

    logger.info("=== Scheduled processing complete ===")


def sync_artist_concerts():
    """가수 키워드 동기화 작업 — 외부 DB에서 가수 키워드를 읽어 Gemini로 내한 콘서트 검색"""
    if not settings.EXTERNAL_DATABASE_URL:
        return

    logger.info("=== Starting artist concert sync ===")

    from core.external_database import get_external_session_factory
    from .sync_service import SyncService

    factory = get_external_session_factory()
    db = factory()

    try:
        service = SyncService(db)
        result = service.sync_all(force=False)
        logger.info(f"Sync result: {result}")
    except Exception as e:
        logger.error(f"Sync error: {e}")
    finally:
        db.close()

    logger.info("=== Artist concert sync complete ===")


def run_scheduler():
    """스케줄러 실행"""
    logger.info("Scheduler started")

    # 즉시 한 번 실행
    process_batch()
    sync_artist_concerts()

    # 주기적 실행
    schedule.every(settings.SCHEDULE_INTERVAL).seconds.do(process_batch)
    schedule.every(settings.SYNC_INTERVAL).seconds.do(sync_artist_concerts)

    while True:
        schedule.run_pending()
        time.sleep(60)


def start_scheduler():
    """스케줄러 백그라운드 시작"""
    if not settings.ENABLE_SCHEDULER:
        logger.info("Scheduler disabled")
        return

    if not settings.GOOGLE_API_KEY:
        logger.warning("Scheduler disabled (no API key)")
        return

    thread = Thread(target=run_scheduler, daemon=True)
    thread.start()
    logger.info("✓ Scheduler started")
