# BEADS — Autonomous Work Units

Each bead is a self-contained, testable unit. Beads can run in parallel where dependencies allow.

## Dependency Graph

```
[B1: Scaffold] ──┬──→ [B2: Discovery] ──→ [B3: PDF Resolver + Downloader] ──→ [B5: Text Extractor]
                 │                                                                     │
                 │                                                            [B5.5: Section Extractor]
                 │                                                                     │
                 │                                                             [B6: LLM Pipeline]
                 │                                                                     │
                 │                                                             [B7: Validator]
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

### B7: JSON Schema Validator — DONE (enhance with Gemini insights)
- Pydantic recursive models (RuleNode, StructuredPolicy)
- Validates operator+rules consistency (both present or both absent)
- `validate_structured_json(data) → (bool, Optional[str])`
- **Gemini enhancements to add**:
  - DFS tree traversal: unique rule_id check, hierarchy prefix validation (child starts with parent prefix)
  - Sequential child ID check (1.1, 1.2, 1.3 not 1.1, 1.3)
  - Empty rule_text detection
  - Depth > 5 warning (possible hallucination)
  - Operator consistency check ("all of the following" → AND, "one of the following" → OR)
  - See `research/2gemini.md` Part D for full implementation

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

### B2: PDF Discovery — READY TO IMPLEMENT (UPGRADED with ChatGPT Deep Research)
- **Depends**: B1, B4
- **Source**: `https://www.hioscar.com/clinical-guidelines/medical`
- **Architecture**: Single-page listing, NO pagination. All guidelines visible in one HTML response.
- **Sections on page**: "Upcoming Policy Changes", "Medical Guidelines" (main list), "Adopted Guidelines"
- **Discovery strategy**:
  1. Parse listing page HTML with requests + BeautifulSoup
  2. Find all `<a>` tags where visible text is exactly `"PDF"` (not "LINK")
  3. Each PDF link's `href` points to an **intermediate policy page** (NOT a direct PDF)
  4. Derive title from nearest `<li>` parent text, strip trailing "PDF"
  5. Title format: `"Acupuncture (CG013, Ver. 11)"` — parse code/version with tolerant regex (optional)
- **CRITICAL**: Links do NOT go directly to `.pdf` files. They go to intermediate pages like:
  - `/medical/cg013v11`, `/medical/cg057v8` (Medical Guidelines)
  - `/pharmacy/pg193v2`, `/pharmacy/cg059v7` (some CG items under /pharmacy/)
  - `/medical/adopted/asam` (Adopted Guidelines)
  - Do NOT assume CG → /medical/ and PG → /pharmacy/. Follow href as ground truth.
- **Dedup**: Listing page has duplicates (nested + top-level). Dedupe by intermediate URL.
- **Filter**: Only process entries with "PDF" link text, skip "LINK" entries (external sites).
- **Store**: UPSERT into policies table with `intermediate_url` as the discovered link
- **Polite**: 0.5s delay + jitter between requests, browser-like User-Agent, 3 retries with backoff
- **robots.txt**: `Allow: /`, no Crawl-delay, clinical guideline pages not disallowed

### B3: PDF Resolver + Downloader — READY TO IMPLEMENT (UPGRADED with ChatGPT Deep Research)
- **Depends**: B2, B4
- **Two-step process** (this is the key insight from ChatGPT research):
  1. **Resolve**: Fetch each intermediate page, parse `__NEXT_DATA__` script tag for real PDF URL
  2. **Download**: Stream-download the actual PDF from `assets.ctfassets.net`
- **PDF URL Resolution** (from intermediate page):
  1. Parse HTML, find `<script id="__NEXT_DATA__">`
  2. `json.loads()` the script content
  3. Recursively walk the JSON for strings containing `ctfassets.net`
  4. Prefer URLs ending in `.pdf`; accept extensionless as fallback
  5. Regex fallback: scan raw HTML for `https?://assets\.ctfassets\.net/[^\s"']+`
- **Real PDF URLs** are on Contentful CDN: `https://assets.ctfassets.net/<space_id>/<asset_id>/<hash>/<filename>.pdf`
- **Download**: Stream with `iter_content(chunk_size=64KB)`, verify `Content-Type: application/pdf`
- **Sanity check**: Reject files < 200 bytes (likely error pages)
- **Size variability**: 6 pages (small) to 113 pages (large) — must handle both
- **Store**: `data/pdfs/` dir, record in downloads table (http_status, error, stored_location)
- **Rate limiting**: 0.5s delay between requests, 3 retries with exponential backoff
- **Session**: reuse `requests.Session()` with browser-like headers for connection pooling

### B5: PDF Text Extractor — READY TO IMPLEMENT (upgraded with Gemini research)
- **Depends**: B3
- **DECISION: Use PyMuPDF (fitz)** — Gemini's comparative analysis is definitive:
  - Flawless Unicode (≥, ≤, ™) — critical for medical thresholds like "BMI ≥ 40"
  - Fastest: < 100ms for 10 pages vs pdfplumber ~1-2s
  - `sort=True` enforces natural reading order, preserving list hierarchy
  - C-based MuPDF engine, superior memory efficiency
- Implementation: `page.get_text("text", sort=True)` per page, join with newlines
- Handle multi-page, preserve numbered list hierarchy (1, a, i)
- Strip headers/footers
- **Grok suggested pdfplumber** but Gemini's analysis shows PyMuPDF better for hierarchical text (pdfplumber better for tables/financial docs)

### B5.5: Initial-Only Section Extractor — NEW (from Gemini research)
- **Depends**: B5
- **Purpose**: Pre-slice PDF text to only the initial criteria BEFORE sending to LLM
- **Implementation**: `extract_initial_criteria(full_text) → (text, confidence, logic_log)`
- **State machine approach** (line-by-line scanning, NOT multi-line regex):
  - START_PATTERNS: `criteria for medically necessary`, `initial (criteria|authorization|approval)`, `medical necessity criteria`, `conditions for coverage`
  - END_PATTERNS: `continuation`, `re-authorization`, `renewal`, `repair/revision`, `experimental/investigational`, `applicable billing codes`, `HCPCS & CPT`
  - Fallback: uppercase headers like "BACKGROUND" or "SUMMARY" as section breaks
- **Confidence scoring**:
  - 0.95 = explicit "Initial" keyword found
  - 0.85 = generic "Criteria for Medically Necessary" found (e.g., CG008 Bariatric)
  - 0.30 = no boundary found, full text passed to LLM (flags for human review)
- **Store confidence + extraction_logic as metadata** for pipeline observability
- Full implementation in `research/2gemini.md` Part B

### B6: LLM Structuring Pipeline — READY TO IMPLEMENT (upgraded with ALL research)
- **Depends**: B5.5, B7
- **API**: OpenAI GPT-4o with `response_format={"type": "json_object"}` (JSON Mode)
  - **NOT Structured Outputs** — Gemini confirmed OpenAI rejects recursive Pydantic models
  - `temperature=0.1` for deterministic analytical mapping
  - `max_tokens=4096`
- **System prompt**: Full medical policy analyst prompt from Gemini (see `research/2gemini.md` Part A)
  - Covers: section identification, hierarchical rule_id generation (dotted notation), leaf vs non-leaf rules, AND/OR detection (explicit triggers, inline connectors, implicit convention), edge cases (cross-refs, inline exceptions, notes)
- **User prompt**: Injects extracted text in `<EXTRACTED_TEXT>` tags with 6-point instruction checklist
- **Initial-only heuristic** (combined from all research):
  - Pre-extraction via B5.5 (regex state machine with confidence scoring)
  - LLM prompt also instructs to stop at continuation/repair/billing boundaries
  - Double protection: regex + prompt
- **Semantic retry logic** (from Gemini):
  - Up to 3 attempts per PDF
  - On validation failure, feed error message back to LLM in next attempt
  - If wrong section detected, append "CRITICAL ERROR: You extracted Continuation criteria"
- **JSON repair** (from Gemini): Use `fast-json-repair` library for malformed LLM output
  - Strip markdown fencing, repair missing brackets/commas
  - Validate repaired JSON with B7
- **Post-processing**: `clean_leaf_nodes()` — remove hallucinated operators from leaf nodes
- **Batch processing**: `asyncio.gather` for concurrent PDF processing
- **Cost**: ~$0.018/PDF, ~$0.28 for 15 PDFs
- Process at least 10 guidelines
- Validate with B7 (Pydantic) before storing
- Store: extracted_text ref, structured_json, llm_metadata (model + prompt version), validation_error, confidence_score

## Research Findings Applied

### Prompt 1 — ChatGPT Deep Research (Scraping Architecture) — NEW
**CRITICAL FINDINGS** that changed B2 and B3:
1. PDF links on listing page → intermediate pages (NOT direct PDFs)
2. Intermediate pages are Next.js SSR — visible HTML is empty, data in `__NEXT_DATA__`
3. Real PDFs on `assets.ctfassets.net` (Contentful CDN)
4. Must parse `__NEXT_DATA__` JSON → recursive walk for `ctfassets.net` URLs
5. Some CG items live under `/pharmacy/` not `/medical/` — follow href, don't assume
6. Listing page has duplicates — dedupe by URL
7. `robots.txt` allows crawling, no Crawl-delay specified
8. PDF sizes vary from 6 to 113 pages
9. PDF headings: "Medical Necessity Criteria for Initial Authorization" vs "Reauthorization"
10. Complete scraper skeleton provided in `research/1chatgpt.md`

### Prompt 3 — ChatGPT (Stack Architecture)
- Confirmed: FastAPI + SQLAlchemy Core (raw SQL) + SQLite WAL
- Confirmed: Vite + React + TS + React Router + Tailwind
- Confirmed: Custom recursive TreeViewer

### Grok Research (`research/groksanswer.md`)
- pdfplumber for text extraction
- LLM prompt template for structuring
- Pydantic for validation (instead of jsonschema)

### Gemini Research (`research/2gemini.md`) — NEW
**Production-grade pipeline blueprint with code. Key contributions:**
1. **System prompt**: Full medical policy analyst prompt with exhaustive edge case handling (Part A)
2. **PDF extraction**: PyMuPDF (fitz) > pdfplumber for clinical guidelines — Unicode, speed, sort=True (Part C)
3. **Section extraction**: State machine with regex START/END patterns + confidence scoring (Part B)
4. **JSON repair**: `fast-json-repair` library for malformed LLM output (Part D)
5. **Tree validation**: DFS traversal with hierarchy prefix, uniqueness, depth, sequential checks (Part D)
6. **OpenAI integration**: JSON Mode (NOT Structured Outputs — recursive schemas rejected), temperature=0.1 (Part E)
7. **Semantic retry**: Feed validation errors back to LLM for self-correction, up to 3 attempts (Part E)
8. **Async batch processing**: `asyncio.gather` for concurrent PDF processing (Part E)
9. **Cost estimate**: ~$0.018/PDF, ~$0.28 for batch of 15 (Part E)
10. **New bead B5.5**: Initial-only section extractor (pre-LLM regex slicing)

## Execution Plan

**Phase 1 — COMPLETE:**
B1, B4, B7, B8, B9, B10 all done and upgraded with research

**Phase 2 — NEXT (all research complete, ready to implement):**
B2 (Discovery) → B3 (Resolver + Downloader) → B5 (Text Extractor) → B5.5 (Section Extractor) → B6 (LLM Pipeline)
- Also: Enhance B7 validator with Gemini DFS traversal checks

**Phase 3 — FINAL:**
Integration test, README updates, commit
