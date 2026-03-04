# BEADS — Autonomous Work Units

Each bead is a self-contained, testable unit. Beads can run in parallel where dependencies allow.

## Dependency Graph

```
[B1: Scaffold] ──┬──→ [B2: Discovery] ──→ [B3: PDF Resolver + Downloader] ──→ [B5: Text Extractor]
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

### B5: PDF Text Extractor — READY TO IMPLEMENT
- **Depends**: B3
- Use pdfplumber (layout-aware text extraction, table support) or PyMuPDF (fitz) for speed
- Handle multi-page, preserve numbered list hierarchy
- Strip headers/footers
- **Grok insight**: pdfplumber superior for structured text; PyMuPDF faster for simple extraction

### B6: LLM Structuring Pipeline — READY TO IMPLEMENT (upgraded with all research)
- **Depends**: B5, B7
- OpenAI GPT-4o with `response_format={"type": "json_object"}`
- System prompt: "You are a medical criteria structurer"
- User prompt: Feed extracted text, request ONLY initial criteria as recursive JSON tree
- **Initial-only heuristic** (from ChatGPT + Grok research):
  - Heading patterns in PDFs:
    - `"Medical Necessity Criteria for Initial Authorization"`
    - `"Medical Necessity Criteria for Reauthorization"` (EXCLUDE)
    - `"Clinical Indications"` → first criteria set = initial
    - `"Continued Care"` / `"Continuation of Services"` (EXCLUDE)
  - Regex: `r'(?:Initial|Medical Necessity Criteria for Initial)\s*(Authorization|Approval|Criteria)'`
  - Strategy: Slice text to initial section, exclude reauth/continuation blocks
  - Fallback: first complete criteria tree if initial/reauth not explicitly labeled
- **Criteria formatting in PDFs** (from ChatGPT research):
  - Numbered lists (1., 2.) with AND/OR logic explicit per line
  - Nested subcriteria: lettered (a., b.) and roman (i., ii.)
  - Bullets: ●, ○, ❖ for drug lists
  - Some policies have multiple indication-specific criteria blocks
- Process at least 10 guidelines
- Validate with B7 (Pydantic) before storing
- Store: extracted_text ref, structured_json, llm_metadata (model + prompt version), validation_error
- Chunk large texts if exceeding token limit; retry with refined prompt on schema failure

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

## Execution Plan

**Phase 1 — COMPLETE:**
B1, B4, B7, B8, B9, B10 all done and upgraded with research

**Phase 2 — NEXT (all research complete, ready to implement):**
B2 (Discovery) → B3 (Resolver + Downloader) → B5 (Extractor) → B6 (LLM Pipeline)

**Phase 3 — FINAL:**
Integration test, README updates, commit
