"""애플리케이션 설정"""
import os

class Settings:
    # Internal Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://admin:password@postgres:5432/keywords"
    )

    # External Database (가수 키워드 소스 & 결과 저장)
    EXTERNAL_DATABASE_URL: str = os.getenv("EXTERNAL_DATABASE_URL", "")

    # AI
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    AI_MODEL: str = "gemini-2.5-flash"

    # Scheduler
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    SCHEDULE_INTERVAL: int = int(os.getenv("SCHEDULE_INTERVAL", "3600"))

    # Sync 설정
    SYNC_INTERVAL: int = int(os.getenv("SYNC_INTERVAL", "3600"))

settings = Settings()
