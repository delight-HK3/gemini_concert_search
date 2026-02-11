# Singer Concert Search

한국 내한 콘서트 정보를 자동으로 수집하고 AI로 분석하는 FastAPI 마이크로서비스입니다.
티켓 사이트(인터파크, 멜론, 티켓링크, 예스24)를 크롤링한 뒤 Google Gemini AI로 데이터를 정제·병합하여 MariaDB에 저장합니다.

## 주요 기능

- **멀티 사이트 크롤링** — 인터파크, 멜론 티켓에서 콘서트 정보 수집
- **AI 분석·정제** — Gemini AI를 활용한 중복 제거, 데이터 정규화, 신뢰도 평가
- **자동 스케줄링** — 백그라운드 데몬 스레드로 주기적 동기화
- **REST API** — 동기화 실행, 결과 조회, 크롤링 원본 데이터 조회

## 파이프라인

```
DB(artist_keyword) → 크롤링(Interpark, Melon) → 원본 저장(crawled_data) → AI 분석(Gemini) → 정제 결과 저장(concert_search_results)
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| Language | Python 3.11 |
| Framework | FastAPI + Uvicorn |
| Database | MariaDB (SQLAlchemy + PyMySQL) |
| AI | Google Generative AI (Gemini 2.5 Flash) |
| Crawling | httpx + BeautifulSoup4 |
| Scheduling | `schedule` 라이브러리 (데몬 스레드) |

## 디렉토리 구조

```
src/
├── main.py                  # FastAPI 앱 진입점, startup hook
├── core/
│   ├── config.py            # 환경 변수 기반 설정
│   └── database.py          # SQLAlchemy 엔진, 세션 관리
├── models/
│   └── external.py          # ORM 모델 (ArtistKeyword, CrawledData, ConcertSearchResult)
├── services/
│   ├── concert_analyzer.py  # Gemini AI 분석 (한국어 프롬프트)
│   ├── crawl_service.py     # 크롤러 통합 실행
│   ├── sync_service.py      # 파이프라인 오케스트레이션
│   └── scheduler.py         # 백그라운드 주기 동기화
├── crawlers/
│   ├── base.py              # 크롤러 공통 인터페이스
│   ├── interpark.py         # 인터파크 크롤러
│   └── melon.py             # 멜론 티켓 크롤러
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
| `DATABASE_URL` | Yes | — | MariaDB 연결 문자열 |
| `GOOGLE_API_KEY` | Yes | — | Google Generative AI API 키 |
| `AI_MODEL` | No | `gemini-2.5-flash` | Gemini 모델명 |
| `ENABLE_SCHEDULER` | No | `true` | 백그라운드 동기화 활성화 여부 |
| `BATCH_SIZE` | No | `10` | 배치 처리 크기 |
| `SYNC_INTERVAL` | No | `3600` | 동기화 주기 (초) |

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
| `GET` | `/health/` | 헬스 체크 (AI, DB 상태) |
| `POST` | `/sync/run?force=false` | 전체 가수 동기화 실행 |
| `POST` | `/sync/run/{artist_name}?force=false` | 특정 가수 동기화 실행 |
| `GET` | `/sync/results?artist_name=` | 콘서트 검색 결과 조회 |
| `GET` | `/sync/results/{artist_keyword_id}` | 특정 가수의 검색 결과 조회 |
| `GET` | `/sync/crawled?artist_name=` | 크롤링 원본 데이터 조회 |

### 사용 예시

```bash
# 전체 동기화 실행
curl -X POST http://localhost:8000/sync/run

# 강제 재동기화 (이미 처리된 가수도 다시 검색)
curl -X POST "http://localhost:8000/sync/run?force=true"

# 특정 가수 동기화
curl -X POST http://localhost:8000/sync/run/BTS

# 검색 결과 조회
curl http://localhost:8000/sync/results?artist_name=BTS

# 크롤링 원본 데이터 조회
curl http://localhost:8000/sync/crawled?artist_name=BTS
```

## 데이터베이스 테이블

- **artist_keyword** (읽기 전용, 사전 등록): `id`, `name`
- **crawled_data** (자동 생성): 크롤링 원본 데이터 — 출처 사이트별 수집 정보
- **concert_search_results** (자동 생성): AI 분석 후 정제된 콘서트 정보 (신뢰도, 교차 검증 여부 포함)

## 라이선스

[MIT License](LICENSE)
