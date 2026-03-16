# Gemini Concert Search

한국 내한 콘서트 정보를 자동으로 수집하고 AI로 분석하는 FastAPI 마이크로서비스입니다.
티켓 사이트(인터파크, 멜론, 티켓링크, 예스24)를 크롤링한 뒤 Google Gemini AI로 데이터를 정제·보강하여 데이터베이스에 저장합니다.
크롤링이 실패한 경우에도 AI 검색으로 폴백하여 데이터를 수집합니다.

## 주요 기능

- **4개 사이트 병렬 크롤링** — 인터파크, 멜론, 티켓링크, Yes24에서 콘서트 정보 동시 수집
- **크롤링 실패 시 AI 검색 폴백** — 크롤링 결과가 없으면 Gemini AI + Google Search로 직접 콘서트 정보 수집
- **AI 분석·정제** — Gemini AI를 활용한 데이터 정규화, 빠진 정보(시간·가격·예매일) 웹 검색 보충, 신뢰도 평가
- **아티스트 검증** — AI로 검색 결과가 실제 해당 아티스트의 공연인지 검증하여 동명이인·부분 문자열 매칭 오검색 방지 (ALI, Ado, REN 등 짧은 이름 대응)
- **증분 갱신 (Upsert)** — 미정이었던 필드(날짜, 시간, 가격, 예매일)가 확정되면 기존 레코드를 자동 갱신
- **날짜 범위 자동 분리** — "2026.02.27~2026.02.28" 같은 다회차 공연을 날짜별 개별 항목으로 분리
- **AI 결과 정합성 보정** — AI가 날짜별 항목을 합치면 크롤링 데이터 기준으로 자동 복원
- **Source/Target DB 분리** — 키워드 읽기 DB(Source)와 결과 저장 DB(Target)를 독립적으로 관리
- **다중 DB 지원** — MySQL, MariaDB, PostgreSQL, SQLite 등 SQLAlchemy 지원 DB 모두 사용 가능
- **자동 스케줄링** — 백그라운드 데몬 스레드로 주기적 동기화
- **REST API** — 동기화 실행, 결과 조회, 크롤링 원본 데이터 조회

## 파이프라인

```
Source DB (artist_keyword)
  │
  ├── 크롤링 (Interpark, Melon, TicketLink, Yes24 병렬)
  │     │
  │     ├── 결과 있음 (크롤링 성공)
  │     │     ├── 날짜 범위 분리 (2/27~2/28 → 2건)
  │     │     ├── 원본 저장 → crawled_data [Target DB]
  │     │     ├── AI 분석 (Gemini + Google Search 보충)
  │     │     ├── AI 결과 정합성 보정 (날짜별 1:1 매핑)
  │     │     └── 정제 결과 저장 → concert_search_results [Target DB]
  │     │     └── AI 결과 정합성 보정 (날짜별 1:1 매핑)
  │     │
  │     └── 결과 없음 (크롤링 실패)
  │           ├── AI 검색 폴백 (Gemini + Google Search 직접 수집)
  │           └── 검색 결과 저장 → concert_search_results [Target DB]
  │           └── AI 검색 폴백 (Gemini + Google Search 직접 수집)
  │
  └── 공통: 지난 공연 필터 → 최종 저장
  ├── 아티스트 검증 (AI가 실제 해당 아티스트의 공연인지 판별)
  ├── 지난 공연 필터
  └── Upsert 저장 → concert_search_results [Target DB]
        ├── 기존 레코드 매칭 → 빈 필드만 갱신
        └── 새 공연 → 신규 삽입
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| Language | Python 3.11 |
| Framework | FastAPI + Uvicorn |
| Database | SQLAlchemy (MySQL, MariaDB, PostgreSQL, SQLite 등) |
| AI | Google Generative AI (Gemini 2.5 Flash) |
| Crawling | httpx + BeautifulSoup4 |

## 디렉토리 구조

```
src/
├── main.py                  # FastAPI 앱 진입점, startup hook
├── core/
│   ├── config.py            # 환경 변수 기반 설정
│   └── database.py          # Source/Target DB 엔진, 세션 관리
├── models/
│   └── external.py          # ORM 모델 (ArtistKeyword, CrawledData, ConcertSearchResult)
├── services/
│   ├── concert_analyzer.py  # Gemini AI 분석 + 크롤링 실패 시 AI 검색 폴백
│   ├── concert_analyzer.py  # Gemini AI 분석 + 아티스트 검증 + AI 검색 폴백
│   ├── crawl_service.py     # 크롤러 통합 실행 (4개 사이트 병렬)
│   ├── sync_service.py      # 파이프라인 오케스트레이션 (크롤링 성공/실패 분기)
│   └── scheduler.py         # 백그라운드 주기 동기화
│   └── sync_service.py      # 파이프라인 오케스트레이션 (upsert 포함)
├── crawlers/
│   ├── base.py              # 크롤러 공통 인터페이스, 날짜 범위 분리, 필터링
│   ├── interpark.py         # 인터파크 크롤러
│   ├── melon.py             # 멜론 티켓 크롤러
│   ├── ticketlink.py        # 티켓링크 크롤러
│   └── yes24.py             # Yes24 티켓 크롤러
└── api/
    ├── schemas.py           # Pydantic 요청/응답 모델
    └── routes/
        ├── health.py        # GET /health/
        └── sync.py          # 동기화 실행 및 결과 조회
```

## 시작하기

### 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `SOURCE_DATABASE_URL` | Yes* | — | 키워드를 읽어올 Source DB 연결 문자열 |
| `TARGET_DATABASE_URL` | Yes* | — | 크롤링·AI 결과를 저장할 Target DB 연결 문자열 |
| `DATABASE_URL` | Yes* | — | Source/Target 미설정 시 단일 DB로 사용 (하위 호환) |
| `GOOGLE_API_KEY` | Yes | — | Google Generative AI API 키 |
| `AI_MODEL` | No | `gemini-2.5-flash` | Gemini 모델명 |
| `ENABLE_SCHEDULER` | No | `true` | 백그라운드 동기화 활성화 여부 |
| `BATCH_SIZE` | No | `10` | 배치 처리 크기 |
| `SYNC_INTERVAL` | No | `3600` | 동기화 주기 (초) |

> \* DB 연결은 `SOURCE_DATABASE_URL` + `TARGET_DATABASE_URL` 조합 또는 `DATABASE_URL` 단독 중 하나 이상 필요합니다.
> `DATABASE_URL`만 설정하면 Source와 Target 모두 동일한 DB를 사용합니다.

**지원 DB 연결 문자열 예시:**

```bash
# MySQL / MariaDB
SOURCE_DATABASE_URL="mysql://user:pass@host:3306/source_db"
TARGET_DATABASE_URL="mariadb://user:pass@host:3306/target_db"

# PostgreSQL
SOURCE_DATABASE_URL="postgresql://user:pass@host:5432/source_db"

# SQLite
TARGET_DATABASE_URL="sqlite:///./concert_results.db"

# 단일 DB (하위 호환)
DATABASE_URL="mysql://user:pass@host:3306/my_db"
```

### 로컬 실행

```bash
pip install -r requirements.txt
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker compose up --build
```

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/` | 서비스 상태 및 설정 정보 |
| `GET` | `/health/` | 헬스 체크 (AI, Source DB, Target DB 상태) |
| `POST` | `/sync/run?force=false` | 전체 가수 동기화 실행 |
| `POST` | `/sync/run/{artist_name}?force=false` | 특정 가수 동기화 실행 |
| `GET` | `/sync/results?artist_name=` | 콘서트 검색 결과 조회 |
| `GET` | `/sync/results/{artist_keyword_id}` | 특정 가수의 검색 결과 조회 |
| `GET` | `/sync/crawled?artist_name=` | 크롤링 원본 데이터 조회 |

### 동기화 모드

| 모드 | 동작 |
|------|------|
| `force=false` (기본) | 전체 파이프라인 실행. 기존 레코드의 빈 필드만 갱신하고, 새 공연은 신규 삽입 |
| `force=true` | 기존 데이터 전부 삭제 후 처음부터 재수집·재삽입 |

### 응답 예시

```json
{
  "total_artists": 50,
  "synced": 50,
  "skipped": 0,
  "concerts_found": 120,
  "concerts_updated": 15
}
```

### 사용 예시

```bash
# 전체 동기화 실행
# 전체 동기화 실행 (기존 레코드 갱신 + 새 공연 추가)
curl -X POST http://localhost:8000/sync/run

# 강제 재동기화 (이미 처리된 가수도 다시 검색)
# 강제 재동기화 (기존 데이터 삭제 후 재수집)
curl -X POST "http://localhost:8000/sync/run?force=true"

# 특정 가수 동기화
curl -X POST http://localhost:8000/sync/run/BTS

# 검색 결과 조회
curl http://localhost:8000/sync/results?artist_name=BTS

# 크롤링 원본 데이터 조회
curl http://localhost:8000/sync/crawled?artist_name=BTS
```

## 데이터베이스 테이블

- **artist_keyword** (Source DB, 읽기 전용, 사전 등록): `id`, `name`
- **crawled_data** (Target DB, 자동 생성): 크롤링 원본 데이터 — 출처 사이트별 수집 정보 (날짜 범위 분리 후 저장)
- **concert_search_results** (Target DB, 자동 생성): AI 분석 후 정제된 콘서트 정보 (신뢰도, 교차 검증 여부, 데이터 출처 포함)

### source 필드 값

| source 값 | 의미 |
|-----------|------|
| `crawl+ai` | 크롤링 데이터를 AI가 정제 |
| `crawl+ai_search` | 크롤링 데이터 + AI 웹 검색으로 빠진 정보 보충 |
| `ai_search` | 크롤링 실패 → AI 검색으로 직접 수집 (confidence 0.3) |

### 증분 갱신 대상 필드

다음 필드가 null 또는 "미정"이었다가 이후 동기화에서 값이 확인되면 자동 갱신됩니다:

| 필드 | 설명 |
|------|------|
| `concert_date` | 공연 날짜 |
| `concert_time` | 공연 시간 |
| `ticket_price` | 티켓 가격 |
| `booking_date` | 예매 시작일 |
| `booking_url` | 예매 링크 |

## 라이선스

[MIT License](LICENSE)
