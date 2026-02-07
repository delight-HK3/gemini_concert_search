"""애플리케이션 설정"""
import os

class Settings:
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://admin:password@postgres:5432/keywords"
    )
    
    # AI
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    AI_MODEL: str = "gemini-2.5-flash"
    
    # Scheduler
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    SCHEDULE_INTERVAL: int = int(os.getenv("SCHEDULE_INTERVAL", "3600"))

settings = Settings()
