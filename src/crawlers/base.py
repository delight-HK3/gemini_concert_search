"""크롤러 공통 인터페이스 및 데이터 모델"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RawConcertData:
    """크롤링된 콘서트 원본 데이터"""
    title: str
    artist_name: str
    venue: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    price: Optional[str] = None
    booking_url: Optional[str] = None
    source_site: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class BaseCrawler(ABC):
    """크롤러 추상 클래스 — 모든 사이트 크롤러의 기반"""

    source_name: str = "unknown"

    @abstractmethod
    async def search(self, artist_name: str) -> List[RawConcertData]:
        """아티스트 이름으로 콘서트 정보 크롤링.

        Args:
            artist_name: 검색할 아티스트 이름

        Returns:
            크롤링된 콘서트 데이터 목록
        """
        pass

    def _log_result(self, artist_name: str, count: int):
        logger.info(f"[{self.source_name}] '{artist_name}' → {count}건 수집")
