"""애플리케이션 설정"""
import os

class Settings:
    # Source DB — 가수 키워드를 읽어오는 DB (읽기 전용)
    SOURCE_DATABASE_URL: str = os.getenv("SOURCE_DATABASE_URL", "")
    # Target DB — 크롤링 원본·AI 분석 결과를 저장하는 DB
    TARGET_DATABASE_URL: str = os.getenv("TARGET_DATABASE_URL", "")

    # 하위 호환: DATABASE_URL만 설정된 경우 source/target 모두 동일 DB 사용
    @property
    def source_db_url(self) -> str:
        return self.SOURCE_DATABASE_URL or os.getenv("DATABASE_URL", "")

    @property
    def target_db_url(self) -> str:
        return self.TARGET_DATABASE_URL or os.getenv("DATABASE_URL", "")

    # AI
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    AI_MODEL: str = "gemini-2.5-flash"

    # Scheduler
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    SYNC_INTERVAL: int = int(os.getenv("SYNC_INTERVAL", "3600"))

settings = Settings()
