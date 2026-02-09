"""애플리케이션 설정"""
import os

class Settings:
    # MariaDB Database (가수 키워드 소스 & 결과 저장)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # AI
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    AI_MODEL: str = "gemini-2.5-flash"

    # Scheduler
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    SYNC_INTERVAL: int = int(os.getenv("SYNC_INTERVAL", "3600"))

settings = Settings()
