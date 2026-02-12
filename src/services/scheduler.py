"""백그라운드 스케줄러"""
import schedule
import time
import logging
from threading import Thread
from core.config import settings

logger = logging.getLogger(__name__)


def sync_artist_concerts():
    """가수 키워드 동기화 작업 — Source DB에서 키워드 읽기 → Target DB에 결과 저장"""
    if not settings.source_db_url or not settings.target_db_url:
        return

    logger.info("=== Starting artist concert sync ===")

    from core.database import get_source_session_factory, get_target_session_factory
    from .sync_service import SyncService

    source_factory = get_source_session_factory()
    target_factory = get_target_session_factory()
    source_db = source_factory()
    target_db = target_factory()

    try:
        service = SyncService(source_db, target_db)
        result = service.sync_all(force=False)
        logger.info(f"Sync result: {result}")
    except Exception as e:
        logger.error(f"Sync error: {e}")
    finally:
        source_db.close()
        target_db.close()

    logger.info("=== Artist concert sync complete ===")


def run_scheduler():
    """스케줄러 실행"""
    logger.info("Scheduler started")

    # 즉시 한 번 실행
    sync_artist_concerts()

    # 주기적 실행
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

    if not settings.source_db_url:
        logger.warning("Scheduler disabled (no SOURCE_DATABASE_URL)")
        return

    if not settings.target_db_url:
        logger.warning("Scheduler disabled (no TARGET_DATABASE_URL)")
        return

    thread = Thread(target=run_scheduler, daemon=True)
    thread.start()
    logger.info("✓ Scheduler started")
