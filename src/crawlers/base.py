"""크롤러 공통 인터페이스 및 데이터 모델"""
from abc import ABC, abstractmethod
import copy
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import List, Optional
import logging
import re

logger = logging.getLogger(__name__)

# 콘서트가 아닌 공연 카테고리 키워드 (제목 앞에 붙거나 포함)
_EXCLUDE_KEYWORDS = [
    "연극", "뮤지컬", "전시", "오페라", "발레",
    "클래식", "국악", "아동", "어린이", "키즈",
]


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

    # ── 공통 필터 ────────────────────────────────────────

    @staticmethod
    def is_concert_title(title: str) -> bool:
        """콘서트/공연 제목인지 확인 (연극·뮤지컬 등 비콘서트 제외)"""
        for kw in _EXCLUDE_KEYWORDS:
            if kw in title:
                return False
        return True

    @staticmethod
    def is_past_event(date_str: Optional[str]) -> bool:
        """공연 날짜가 이미 지났는지 확인

        범위 날짜(2026.03.28~2026.03.29)면 종료일 기준으로 판단.
        날짜 파싱 실패 시 False(제외하지 않음).
        """
        if not date_str:
            return False

        today = date.today()

        # 날짜 문자열에서 YYYY.MM.DD 또는 YYYY-MM-DD 패턴 추출
        dates = re.findall(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", date_str)
        if not dates:
            return False

        try:
            # 마지막 날짜(종료일)를 기준으로 판단
            y, m, d = dates[-1]
            end_date = date(int(y), int(m), int(d))
            return end_date < today
        except (ValueError, IndexError):
            return False

    @staticmethod
    def _expand_date_ranges(results: List[RawConcertData]) -> List[RawConcertData]:
        """범위 날짜(2026.02.27~2026.02.28)를 개별 항목으로 분리

        하나의 크롤링 항목에 날짜가 여러 개이면 각 날짜별로 별도 항목을 생성한다.
        """
        expanded = []
        for item in results:
            if not item.date:
                expanded.append(item)
                continue

            dates = re.findall(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", item.date)
            if len(dates) <= 1:
                expanded.append(item)
                continue

            # 날짜가 여러 개이면 각각 별도 항목 생성
            for y, m, d in dates:
                new_item = copy.copy(item)
                new_item.date = f"{y}.{int(m):02d}.{int(d):02d}"
                expanded.append(new_item)

        return expanded

    def filter_results(self, results: List[RawConcertData]) -> List[RawConcertData]:
        """범위 날짜 분리 → 비콘서트 제외 → 지난 공연 제외"""
        # 1) 범위 날짜를 개별 항목으로 분리
        results = self._expand_date_ranges(results)

        # 2) 비콘서트·지난 공연 제외
        filtered = []
        for item in results:
            if not self.is_concert_title(item.title):
                logger.debug(f"[{self.source_name}] 비콘서트 제외: {item.title}")
                continue
            if self.is_past_event(item.date):
                logger.debug(f"[{self.source_name}] 지난 공연 제외: {item.title} ({item.date})")
                continue
            filtered.append(item)
        return filtered
