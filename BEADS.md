# BEADS — Autonomous Work Units

Each bead is a self-contained, testable unit. Beads can run in parallel where dependencies allow.

## Dependency Graph

```
[B1: Scaffold] ──┬──→ [B2: Discovery] ──→ [B3: Downloader] ──→ [B5: Text Extractor]
                 │                                                      │
                 │                                              [B6: LLM Pipeline]
                 │                                                      │
                 │                                              [B7: Validator]
                 │
                 ├──→ [B4: Database Layer] (parallel with B2)
                 │
                 └──→ [B8: API Server] ──→ [B9: UI List] ──→ [B10: UI Tree]
```

## Bead Status

### B1: Project Scaffold — DONE
- FastAPI + Vite/React/TS + SQLite
- All deps installed, dev servers boot

### B4: Database Layer — DONE (upgraded with research)
- SQLAlchemy Core + raw SQL (not ORM) per research recommendation
- SQLite with WAL mode, foreign keys, busy_timeout=5000
- Schema in `backend/sql/sqlite_schema.sql` with CREATE TABLE IF NOT EXISTS
- UPSERT patterns: `ON CONFLICT(pdf_url) DO UPDATE` for policies, `ON CONFLICT(policy_id) DO UPDATE` for structured_policies
- Auto-migration on FastAPI startup via `backend/migrate.py`

### B7: JSON Schema Validator — DONE
- Pydantic recursive models (RuleNode, StructuredPolicy)
- Validates operator+rules consistency (both present or both absent)
- `validate_structured_json(data) → (bool, Optional[str])`

### B8: API Server — DONE (upgraded with research)
- 4 endpoints with raw SQL queries:
  - `GET /api/policies` — list with LEFT JOIN latest_download + structured existence
  - `GET /api/policies/:id` — detail with download + structured data
  - `GET /api/policies/:id/tree` — structured JSON tree directly
  - `GET /api/stats` — counts for policies/downloaded/failed/structured
- CORS for Vite dev server (localhost:5173)
- `_parse_json_maybe()` handles SQLite TEXT ↔ Python dict

### B9: UI — Policy List — DONE (upgraded with research)
- Table with title (linked), PDF link, download badge, structured badge
- Search filter by title
- react-router-dom Link to detail view

### B10: UI — Tree Viewer — DONE (upgraded with research)
- Custom recursive component (no library needed for ~50-100 nodes)
- Expand/collapse per node, default expand depth 0-1
- AND = blue badge, OR = orange badge, leaf = checkmark icon
- Expand All / Collapse All buttons
- Legend bar, rule_id monospace labels, connector lines
- React.memo for performance

### B2: PDF Discovery (Scraper) — READY TO IMPLEMENT
- **Depends**: B1, B4
- Scrape https://www.hioscar.com/clinical-guidelines/medical
- Find all `<a>` tags with href starting `/medical/cg*`
- Resolve relative URLs to full `https://www.hioscar.com/medical/cgXXX`
- UPSERT into policies table: `INSERT ... ON CONFLICT(pdf_url) DO UPDATE`
- **Research insight**: Use requests + BeautifulSoup, `User-Agent` header, polite delays 1-2s
- **Grok insight**: If page is JS-loaded, fallback to Selenium; use regex `cg\d+v\d+` for link pattern matching

### B3: PDF Downloader — READY TO IMPLEMENT
- **Depends**: B2
- Download each PDF to `data/pdfs/` dir
- Use `tenacity` for retry 3x with exponential backoff (`wait_exponential(min=4, max=10)`)
- 2s delay between requests for polite scraping
- Detect content-type (`application/pdf`) to verify actual PDF
- Record in downloads table (http_status, error, stored_location)

### B5: PDF Text Extractor — READY TO IMPLEMENT
- **Depends**: B3
- Use pdfplumber (layout-aware text extraction, table support) or PyMuPDF (fitz) for speed
- Handle multi-page, preserve numbered list hierarchy
- Strip headers/footers
- **Grok insight**: pdfplumber superior for structured text; PyMuPDF faster for simple extraction

### B6: LLM Structuring Pipeline — READY TO IMPLEMENT (unblocked by Grok research)
- **Depends**: B5, B7
- OpenAI GPT-4o with `response_format={"type": "json_object"}`
- System prompt: "You are a medical criteria structurer"
- User prompt: Feed extracted text, request ONLY initial criteria as recursive JSON tree
- **Initial-only heuristic**: Scan text for keywords ("Initial Criteria", "Initial Approval", "Initial Authorization") via regex `r'Initial\s*(Criteria|Approval)'`; slice text to that section. Fallback: use first criteria-like section after "Medical Necessity" header
- Process at least 10 guidelines (use `random.sample` from unstructured policies)
- Validate with B7 (Pydantic) before storing
- Store: extracted_text ref, structured_json, llm_metadata (model + prompt version), validation_error
- **Grok insight**: Chunk large texts if exceeding token limit; retry with refined prompt on schema failure

## Research Findings Applied (Prompt 3 — ChatGPT)

### Confirmed Stack
- FastAPI + SQLAlchemy Core (raw SQL via `text()`) — NOT ORM
- SQLite + WAL mode (single file, no server, concurrent reads)
- Vite + React + TypeScript + React Router + Tailwind CSS
- Custom recursive TreeViewer (no react-d3-tree, no react-arborist)

### Key Patterns
- `check_same_thread=False` for SQLite in web server
- `pool_pre_ping=True` for connection health
- WAL + busy_timeout=5000 for concurrent access
- JSON stored as TEXT in SQLite, parsed with `_parse_json_maybe()`
- CTE with `ROW_NUMBER() OVER (PARTITION BY)` for latest download
- `createBrowserRouter` with Layout route wrapping pages

### Research Gaps — RESOLVED (Grok research in `research/groksanswer.md`)
- Scraping: Links are `/medical/cg*` pattern, use BS4 + requests with User-Agent
- LLM pipeline: Prompt template confirmed, initial-only via keyword regex + text slicing
- PDF extraction: pdfplumber recommended for layout-aware extraction
- Validation: jsonschema with recursive `$ref` (we use Pydantic instead — equivalent)

## Execution Plan

**Phase 1 — COMPLETE:**
B1, B4, B7, B8, B9, B10 all done and upgraded with research

**Phase 2 — NEXT (research complete, ready to implement):**
B2 (Discovery), B3 (Downloader), B5 (Extractor), B6 (LLM Pipeline)

**Phase 3 — FINAL:**
Integration test, README updates, commit
