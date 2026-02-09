# CLAUDE.md

## Project Overview

**gemini-db-search** is a FastAPI microservice that searches for Korean concert information using Google Gemini AI. It reads artist keywords from a MariaDB database, queries Gemini for concert details, and stores results back in the database. Version 5.0.0, MIT licensed.

## Directory Structure

```
src/
├── main.py                  # FastAPI app entry point, startup hooks
├── core/
│   ├── config.py            # Settings via environment variables
│   └── database.py          # SQLAlchemy engine, session management
├── models/
│   └── external.py          # ORM models: ArtistKeyword, ConcertSearchResult
├── services/
│   ├── concert_analyzer.py  # Gemini AI integration (Korean prompts)
│   ├── sync_service.py      # Orchestration: read artists → query AI → save results
│   └── scheduler.py         # Background daemon thread for periodic sync
└── api/
    ├── schemas.py           # Pydantic request/response models
    └── routes/
        ├── health.py        # GET /health/
        └── sync.py          # POST /sync/run, GET /sync/results
```

## Tech Stack

- **Language:** Python 3.11
- **Framework:** FastAPI + Uvicorn
- **Database:** MariaDB via SQLAlchemy + PyMySQL
- **AI:** Google Generative AI (Gemini, default model: `gemini-2.5-flash`)
- **Scheduling:** `schedule` library in a daemon thread

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | MariaDB connection string |
| `GOOGLE_API_KEY` | Yes | — | Google Generative AI key |
| `AI_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `ENABLE_SCHEDULER` | No | `true` | Background sync on/off |
| `BATCH_SIZE` | No | `10` | Batch processing size |
| `SYNC_INTERVAL` | No | `3600` | Sync interval in seconds |

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server locally
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# Docker
docker compose up --build
```

There are no test suites, linters, or CI pipelines configured in this project.

## API Endpoints

- `GET /` — Service status and configuration info
- `GET /health/` — Health check (ai_enabled, db_configured)
- `POST /sync/run?force=false` — Trigger concert sync for all artists
- `GET /sync/results?artist_name=` — List concert search results
- `GET /sync/results/{artist_keyword_id}` — Results for a specific artist

## Architecture & Patterns

- **Layered architecture:** core → models → services → api
- **Dependency injection:** FastAPI `Depends()` for DB sessions
- **Lazy init:** Database engine created on first use
- **Connection string normalization:** `mysql://` or `mariadb://` → `mysql+pymysql://`
- **JSON extraction:** Parses Gemini responses that may be wrapped in markdown code blocks
- **Deduplication:** Skips already-synced artists unless `force=true`

## Database Tables

- **artist_keyword** (read-only, pre-existing): `id`, `name`
- **concert_search_results** (auto-created on startup): stores concert details per artist including title, venue, date, time, price, booking info, raw AI response, and sync timestamp

## Code Conventions

- Comments and docstrings are in **Korean**
- Type hints used throughout
- Pydantic models for all API schemas
- SQLAlchemy ORM for database access
- Error handling with logging in service layer
- No tests or linting configured — validate manually

## Key Implementation Notes

- The Gemini prompt is in Korean and asks for structured JSON output with concert fields
- Empty results are stored as `raw_response: "[]"` to mark an artist as synced
- The scheduler runs in a daemon thread and does not block the API server
- The app degrades gracefully when `GOOGLE_API_KEY` or `DATABASE_URL` are missing
