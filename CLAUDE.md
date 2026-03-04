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
- `backend/scraper.py` — B2+B3: Discovery + PDF resolver + downloader (requests + BS4 + __NEXT_DATA__)
- `backend/extractor.py` — B5+B5.5: PDF text extraction (PyMuPDF) + initial section extraction
- `backend/structurer.py` — B6: LLM structuring pipeline (OpenAI GPT-4o + JSON mode)
- `backend/interfaces.py` — Protocol contracts for each pipeline bead
- `frontend/src/components/TreeViewer.tsx` — Recursive tree with expand/collapse, AND/OR badges
- `AGENTS.md` — Agent instructions for bd workflow
- `BEADS.md` — Legacy reference (details per bead). Live tracking now in `bd` database

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
- `POST /api/run-scraper` — Trigger B2+B3 pipeline (discover + resolve + download all PDFs)
- `POST /api/run-structurer` — Trigger B5+B6 pipeline (extract text + LLM structuring, limit=10)

## Scraping Architecture (from ChatGPT Deep Research)

- **Listing page** (`/clinical-guidelines/medical`): Single HTML page, no pagination
- **PDF links are NOT direct**: `<a>` tags with text "PDF" → **intermediate pages** (e.g., `/medical/cg013v11`)
- **Intermediate pages**: Next.js SSR — parse `<script id="__NEXT_DATA__">` JSON for real PDF URL
- **Real PDF host**: `assets.ctfassets.net` (Contentful CDN)
- **Resolution**: Recursively walk `__NEXT_DATA__` JSON for `ctfassets.net` URLs, prefer `.pdf` suffix
- **URL prefixes vary**: `/medical/cg*`, `/pharmacy/pg*`, `/pharmacy/cg*`, `/medical/adopted/*` — follow href
- **Dedup by intermediate URL** (listing has duplicates)
- **Filter**: Only "PDF" link text, skip "LINK" entries
- **Complete scraper skeleton**: `research/1chatgpt.md`

## Critical Constraints

- **Initial criteria only**: Extract only the Initial tree (not Continuation/Repair/Revision)
- **Initial heading patterns**: "Medical Necessity Criteria for Initial Authorization", "Clinical Indications" (first block)
- **Exclude patterns**: "Reauthorization", "Continued Care", "Continuation of Services"
- **Idempotent reruns**: `pdf_url` UNIQUE + UPSERT patterns
- **Polite scraping**: 0.5s delay + jitter, retry 3x with backoff, browser-like User-Agent
- **Schema validation**: Pydantic recursive model validation before DB insert

## Issue Tracking — bd (beads)

This project uses **bd** (Steve Yegge's Beads) for ALL task tracking. Backed by Dolt (version-controlled SQL). See AGENTS.md for full agent workflow.

```bash
bd ready              # Find unblocked work — START HERE every session
bd show <id>          # View issue details + description
bd update <id> --claim  # Claim work atomically
bd close <id> --reason "Done"  # Complete work
bd list               # List all open issues
bd graph --all        # Visualize dependency chain
bd create "title" -d "context" -t feature -p 1  # Create new issue
```

**Rules:**
- Do NOT use markdown TODOs, TASKS.md, or competing task files — bd is the single source of truth
- Always `bd ready` before starting work to find unblocked issues
- Create discovered issues with `bd create "title" -d "context" --deps discovered-from:<parent-id>`
- Include bead ID in commit messages: `git commit -m "Add scraper (full-stack-feb-mw1)"`
- When closing a bead, update bd BEFORE merging to main: `bd close <id> --reason "Completed"`
- Never use `bd edit` (interactive) — use `bd update <id> --description "text"` instead

## Git Workflow (parallel-safe, beads-integrated)

**Multiple Claude sessions may run simultaneously on different branches.**

### Session Start
```bash
cd /home/gian/Projects/full-stack-feb/full-stack-feb
git checkout main && git pull origin main
git checkout -b <descriptive-branch-name>   # e.g. scraper, llm-pipeline, ui-tree
bd ready                                     # Find what to work on
bd update <id> --claim                       # Claim the bead
```

### While Working
- **Commit + push after EVERY meaningful change** (new file, function complete, bug fix)
- `git add <files> && git commit -m "description (bead-id)" && git push origin <branch>`
- Aim for a commit+push every 5-10 minutes — unpushed work is LOST if session dies

### Before Merge to Main (MANDATORY)
```bash
# TypeScript type-check MUST pass before any merge to main
npx tsc --noEmit
```
If `tsc` fails, fix ALL type errors on your feature branch before proceeding.

### Merge to Main (end of session)
```bash
git add -A && git commit -m "final changes (bead-id)" && git push origin <branch>
bd close <id> --reason "Completed"           # Close the bead FIRST
git checkout main && git pull origin main     # Get latest
git checkout <branch>                         # Back to feature branch
git merge main                               # Merge main INTO branch (resolve conflicts here)
npx tsc --noEmit                             # Type-check MUST pass
git checkout main && git merge <branch>       # Fast-forward merge to main
git push origin main
git push origin --delete <branch> && git branch -d <branch>
```

### Critical Rules
- NEVER `git push --force` to main
- NEVER merge to main without `npx tsc --noEmit` passing first
- ALWAYS resolve conflicts on the feature branch, not on main
- If `git push origin main` fails (another session pushed), repeat the merge steps
- Before merging, check `git log origin/main --oneline -5` for other sessions' work

## Commands

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Type-check (required before merge)
cd frontend && npx tsc --noEmit

# Validate oscar.json
python backend/validator.py
```
