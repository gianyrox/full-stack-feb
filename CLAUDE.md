# CLAUDE.md

## Project Overview

Oscar Medical Guidelines scraper + structured criteria tree explorer. The system:
1. Discovers and downloads all medical guideline PDFs from https://www.hioscar.com/clinical-guidelines/medical
2. Uses an LLM (OpenAI) to structure at least 10 guidelines' **initial** medical necessity criteria into JSON decision trees
3. Persists scraped policy metadata and structured trees in a database
4. Provides a UI to browse policies and navigate/render criteria trees

## Architecture (confirmed by research)

- **Backend**: FastAPI + SQLAlchemy Core (raw SQL via `text()`, NOT ORM) + SQLite (WAL mode)
- **Frontend**: Vite + React + TypeScript + React Router + Tailwind CSS
- **Tree rendering**: Custom recursive component (no third-party library)
- **DB**: SQLite at `data/app.db`, auto-migrated on startup from `backend/sql/sqlite_schema.sql`

## Key Files

- `oscar.json` — Target JSON structure. Recursive: `{title, insurance_name, rules: {rule_id, rule_text, operator?, rules?[]}}`
- `backend/main.py` — FastAPI app with 4 endpoints (policies list, detail, tree, stats) using raw SQL with CTEs
- `backend/sql/sqlite_schema.sql` — Schema DDL (3 tables + indexes)
- `backend/migrate.py` — Runs schema SQL at startup
- `backend/validator.py` — Pydantic recursive validation of LLM output
- `backend/interfaces.py` — Protocol contracts for each pipeline bead
- `frontend/src/components/TreeViewer.tsx` — Recursive tree with expand/collapse, AND/OR badges
- `BEADS.md` — Work unit tracker with status and dependencies

## Database Patterns

- SQLite pragmas: `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`
- `check_same_thread=False` for web server threading
- Policy UPSERT: `INSERT ... ON CONFLICT(pdf_url) DO UPDATE`
- Structured UPSERT: `INSERT ... ON CONFLICT(policy_id) DO UPDATE`
- Latest download: CTE with `ROW_NUMBER() OVER (PARTITION BY policy_id ORDER BY downloaded_at DESC)`
- JSON stored as TEXT, parsed with `_parse_json_maybe()`

## API Endpoints

- `GET /api/policies` — List all with download_status + has_structured_tree
- `GET /api/policies/:id` — Detail with latest download + structured data
- `GET /api/policies/:id/tree` — Raw structured JSON tree
- `GET /api/stats` — Counts: total_policies, downloaded, failed, structured

## Critical Constraints

- **Initial criteria only**: Extract only the Initial tree (not Continuation/Repair/Revision)
- **Idempotent reruns**: `pdf_url` UNIQUE + UPSERT patterns
- **Polite scraping**: 1-2s delays, retry 3x with exponential backoff
- **Schema validation**: Pydantic recursive model validation before DB insert

## Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Validate oscar.json
python backend/validator.py
```
