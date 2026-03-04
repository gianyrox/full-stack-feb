# Research Prompts for Oscar Medical Guidelines Project

These prompts are designed to be used with ChatGPT Deep Research and Gemini Deep Research to gather everything needed to implement the full project. Each prompt is self-contained with all context embedded.

---

## PROMPT 1 — ChatGPT Deep Research: Scraping Oscar's Clinical Guidelines (Discovery + Download + Site Architecture)

```
I am building a Python scraper that must discover and download ALL medical guideline PDFs from Oscar Health's clinical guidelines page. This is a timed coding challenge (2 hours). I need you to do exhaustive research so I can implement without guessing.

=== THE SOURCE PAGE ===
URL: https://www.hioscar.com/clinical-guidelines/medical

This page lists all of Oscar's medical clinical guidelines. Each guideline links to a policy page (example: https://www.hioscar.com/medical/cg013v11), and from there I need to find and download the actual PDF.

=== WHAT I NEED YOU TO RESEARCH (BE EXHAUSTIVE) ===

### 1. SOURCE PAGE ARCHITECTURE
Visit https://www.hioscar.com/clinical-guidelines/medical and tell me:
- Is it server-side rendered HTML or a JavaScript SPA that loads content dynamically?
- If it's an SPA (React/Next.js/etc.), what framework? Does it fetch data from an API endpoint I could hit directly?
- Inspect the network tab: are there XHR/fetch calls that return JSON with the guideline list? If so, what is the exact API URL, request headers, and response shape?
- How many total medical guidelines are listed on the page?
- Is there pagination, infinite scroll, "load more" buttons, or tabs that hide some guidelines?
- What does the HTML structure look like? Give me the exact CSS selectors or XPath to extract each guideline link and its title text
- Are the links `<a href="/medical/cg008v10">` style relative links, or full URLs, or something else?
- What is the URL pattern? Is it always `/medical/cgXXXvYY` where XXX is guideline number and YY is version?
- Are there non-medical guidelines mixed in that I need to filter out?
- Does the page have any category filters, sections, or groupings I should be aware of?

### 2. INDIVIDUAL POLICY PAGES → PDF ACCESS
Visit several individual policy pages (at least 3-4 different ones) and tell me:
- Example policy page: https://www.hioscar.com/medical/cg013v11
- On each policy page, how is the PDF presented? Is it:
  (a) A direct download link (`<a href="something.pdf">`)
  (b) An embedded PDF viewer (`<embed>`, `<iframe>`, `<object>`)
  (c) A JavaScript-based PDF viewer (pdf.js, Google Docs viewer, etc.)
  (d) The PDF content rendered as HTML on the page itself
  (e) A redirect to a CDN/S3 URL
- What is the actual PDF download URL? Give me the full URL pattern for at least 3 examples
- Are PDFs hosted on the same domain (hioscar.com) or a CDN (e.g., S3, CloudFront, etc.)?
- Do the PDF URLs contain version numbers, hashes, or timestamps?
- Are there any query parameters, tokens, or cookies required to access the PDFs?
- What Content-Type header does the PDF response return?
- What is the typical file size range for these PDFs?
- Can I get the PDF URL directly from the source page without visiting each individual policy page? (This would save many HTTP requests)

### 3. COMPLETE GUIDELINE INVENTORY
- List ALL medical guidelines you can find on the source page with their:
  - Title/name
  - URL pattern (e.g., /medical/cg008v10)
  - Guideline code (e.g., CG008)
  - Version number
- How many total are there?
- Are there guidelines that have multiple versions listed, or only the latest version?

### 4. ANTI-SCRAPING & RATE LIMITING
- Check https://www.hioscar.com/robots.txt — what paths are allowed/disallowed? What crawl-delay is specified?
- Does the site use Cloudflare, Akamai, AWS WAF, or any other CDN/WAF protection?
- Are there CAPTCHA challenges or JavaScript challenges on any pages?
- What User-Agent strings work? Does it block common bot User-Agents?
- Are there rate limits? What happens if you make rapid sequential requests?
- Does the site require cookies from an initial page load (session cookies)?
- Are there any CORS headers or CSP policies that affect scraping?
- What HTTP status codes does it return for rate-limited or blocked requests?

### 5. TECHNOLOGY STACK DETECTION
- What technology stack does hioscar.com use? (Check Wappalyzer, BuiltWith, or page source)
- Is it Next.js, Gatsby, a custom React app, or server-rendered?
- Does it use a headless CMS or API backend?
- This matters because it determines whether I need a headless browser (Playwright/Selenium) or if plain HTTP requests (requests/httpx) will work

### 6. IMPLEMENTATION RECOMMENDATIONS
Based on your findings, tell me:
- Should I use `requests`/`httpx` + `BeautifulSoup`, or do I need Playwright/Selenium for JavaScript rendering?
- If I need a headless browser, what's the minimal approach (e.g., just for the listing page, then direct HTTP for PDFs)?
- What's the optimal scraping strategy to discover ALL PDFs in the fewest HTTP requests?
- Give me a concrete code skeleton in Python that would:
  1. Fetch the source page and extract all guideline links + titles
  2. For each guideline, get the PDF download URL
  3. Download the PDF with proper error handling
  4. Include rate limiting (time.sleep between requests) and retry logic (exponential backoff)
  5. Include proper headers (User-Agent, Accept, Referer) to avoid blocks
- What Python libraries should I use? (requests vs httpx vs aiohttp, beautifulsoup4 vs lxml vs selectolax, etc.)

### 7. EDGE CASES & GOTCHAS
- Are there any guidelines that DON'T have PDFs?
- Are there broken links or redirects?
- Are there guidelines that link to external sites instead of Oscar PDFs?
- Do any PDFs require login/authentication?
- Are there guidelines with multiple PDFs (e.g., appendices)?
- What happens if you request a non-existent guideline URL?

Give me CONCRETE answers with real URLs, HTML snippets, HTTP responses, and code examples. I cannot afford to guess — I have 2 hours total for the entire project and this scraping is just one component.
```

---

## PROMPT 2 — Gemini Deep Research: PDF Text Extraction + LLM Structuring Pipeline + "Initial Only" Detection

```
I am building a pipeline that extracts text from Oscar Health medical guideline PDFs, identifies the "Initial" medical necessity criteria section, sends it to an LLM (OpenAI GPT-4o), and produces a structured JSON decision tree. This is for a timed coding challenge. I need exhaustive, production-ready guidance.

=== THE EXACT TARGET JSON FORMAT ===

Here is a real example (Bariatric Surgery guideline, abbreviated) that I must match EXACTLY:

{
    "title": "Medical Necessity Criteria for Bariatric Surgery",
    "insurance_name": "Oscar Health",
    "rules": {
        "rule_id": "1",
        "rule_text": "Procedures are considered medically necessary when ALL of the following criteria are met",
        "operator": "AND",
        "rules": [
            {
                "rule_id": "1.1",
                "rule_text": "Informed consent with appropriate explanation of risks, benefits, and alternatives"
            },
            {
                "rule_id": "1.2",
                "rule_text": "Adult aged 18 years or older with documentation of",
                "operator": "OR",
                "rules": [
                    {
                        "rule_id": "1.2.1",
                        "rule_text": "Body mass index (BMI) ≥40"
                    },
                    {
                        "rule_id": "1.2.2",
                        "rule_text": "BMI greater ≥35 with ONE of the following severe obesity-related comorbidities",
                        "operator": "OR",
                        "rules": [
                            {"rule_id": "1.2.2.1", "rule_text": "Clinically significant cardio-pulmonary disease (e.g. severe obstructive sleep apnea (OSA), obesity-hypoventilation syndrome (OHS))"},
                            {"rule_id": "1.2.2.2", "rule_text": "Coronary artery disease, objectively documented via stress test, echocardiography, angiography, prior myocardial infarction, or similar"},
                            {"rule_id": "1.2.2.3", "rule_text": "Objectively documented cardiomyopathy"},
                            {"rule_id": "1.2.2.4", "rule_text": "Medically refractory hypertension (defined as > 140 mmHg systolic and/or 90 mmHg diastolic despite concurrent use of 3 antihypertensive agents)"},
                            {"rule_id": "1.2.2.5", "rule_text": "Type 2 diabetes mellitus"},
                            {"rule_id": "1.2.2.6", "rule_text": "Nonalcoholic fatty liver disease or nonalcoholic steatohepatitis"},
                            {"rule_id": "1.2.2.7", "rule_text": "Osteoarthritis of the knee or hip or improving outcomes of knees or hip replacement"},
                            {"rule_id": "1.2.2.8", "rule_text": "Urinary stress incontinence"}
                        ]
                    },
                    {"rule_id": "1.2.3", "rule_text": "BMI ≥30-34.9, see section below"}
                ]
            },
            {"rule_id": "1.3", "rule_text": "Failure to achieve and maintain successful long-term weight loss via non-surgical therapy"},
            {
                "rule_id": "1.4",
                "rule_text": "The proposed bariatric surgery includes a comprehensive pre- and post-operative plan",
                "operator": "AND",
                "rules": [
                    {
                        "rule_id": "1.4.1",
                        "rule_text": "Preoperative evaluation to rule out and treat any other reversible causes of weight gain/obesity",
                        "operator": "AND",
                        "rules": [
                            {"rule_id": "1.4.1.1", "rule_text": "Basic laboratory testing (blood glucose, lipid panel, CBC, metabolic panel, blood typing, coagulation studies)"},
                            {"rule_id": "1.4.1.2", "rule_text": "Nutrient deficiency screening and formal nutrition evaluation"},
                            {"rule_id": "1.4.1.3", "rule_text": "Cardiopulmonary risk evaluation"},
                            {"rule_id": "1.4.1.4", "rule_text": "GI evaluation"},
                            {"rule_id": "1.4.1.5", "rule_text": "Endocrine evaluation"},
                            {"rule_id": "1.4.1.6", "rule_text": "Age appropriate cancer screening verified complete and up to date"},
                            {"rule_id": "1.4.1.7", "rule_text": "Smoking cessation counseling, if applicable"}
                        ]
                    }
                ]
            },
            {
                "rule_id": "1.5",
                "rule_text": "Psycho-social behavioral evaluation",
                "operator": "AND",
                "rules": [
                    {"rule_id": "1.5.1", "rule_text": "No current substance abuse has been identified"},
                    {
                        "rule_id": "1.5.2",
                        "rule_text": "Members who have any of the following conditions MUST have formal, documented preoperative psychological clearance",
                        "operator": "OR",
                        "rules": [
                            {"rule_id": "1.5.2.1", "rule_text": "A history of schizophrenia, borderline personality disorder, suicidal ideation, severe depression"},
                            {"rule_id": "1.5.2.2", "rule_text": "Who are currently under the care of a psychologist/psychiatrist"},
                            {"rule_id": "1.5.2.3", "rule_text": "Who are on psychotropic medications"}
                        ]
                    }
                ]
            }
        ]
    }
}

=== WHAT THE ACTUAL PDF TEXT LOOKS LIKE (REAL EXAMPLE) ===

I've examined the Bariatric Surgery PDF (CG008, Ver. 10). Here's the ACTUAL structure:

The PDF has these sections in order:
1. Header: "Oscar Clinical Guideline: Bariatric Surgery (Adults) (CG008, Ver. 10)"
2. Title: "Bariatric Surgery (Adults)"
3. Disclaimer box (boilerplate)
4. Summary (paragraph of medical background)
5. Definitions (terms like BMI, Class I/II/III Obesity, Open Surgery, Laparoscopic Surgery, etc.)
6. Clinical Indications — "Procedures & Length of Stay" (lists procedures with settings/LOS)
7. "Length of Stay (LOS) Extensions" section
8. >>> "Criteria for Medically Necessary Procedures" <<< THIS IS THE TARGET SECTION
   - Starts with "Procedures are considered medically necessary when ALL of the following criteria are met:"
   - Uses numbered lists: 1, 2, 3, 4, 5 (top level)
   - Sub-items use letters: a, b, c (second level)
   - Sub-sub-items use roman numerals: i, ii, iii, iv (third level)
   - Sub-sub-sub-items use numbers again: 1, 2 (fourth level)
   - Logic connectors appear as italicized words at the end of lines: "and", "or"
   - Example: "1. Informed consent...; and" (the "and" tells you it's AND logic with sibling items)
   - Example: "a. Body mass index (BMI) ≥40; or" (the "or" tells you it's OR logic with siblings)
9. "Members with a BMI 30-34.9" section (additional criteria for edge case)
10. "Repair, Replacement, Removal, Revision, or Conversion Procedures" (separate criteria trees for each — these are NOT the "initial" criteria)
11. "Experimental or Investigational / Not Medically Necessary" (exclusion list)
12. "Relative Contraindications" section
13. "Applicable Billing Codes (HCPCS & CPT Codes)" table
14. References

CRITICAL OBSERVATIONS ABOUT THE PDF FORMAT:
- The "and"/"or" connectors at the end of list items (often italicized, with semicolons) are THE KEY to determining AND vs OR logic
- "ALL of the following" in a parent = AND operator
- "ONE of the following" or "any of the following" in a parent = OR operator
- The numbered/lettered/roman-numeral hierarchy maps directly to the rule_id hierarchy (1 → 1.1 → 1.1.1 → 1.1.1.1)
- Some PDFs have BOTH "Initial" and "Continuation" criteria sections (the bariatric one doesn't explicitly label them, but others like cg013v11 do)
- Some PDFs have MULTIPLE distinct criteria trees (e.g., one for the primary procedure, separate ones for Repair, Revision, Conversion)
- The "initial" criteria is typically the FIRST major "Criteria for Medically Necessary Procedures" section, before any "Continuation", "Renewal", or "Reauthorization" sections

=== WHAT I NEED FROM YOU ===

### PART A: OPTIMAL LLM PROMPTS (copy-paste ready)

Give me the EXACT system prompt and user prompt template I should use with GPT-4o to convert extracted PDF text into the JSON format above. The prompts must handle:

1. **Section identification**: Instruct the LLM to find and ONLY parse the "Initial" or first "Criteria for Medically Necessary Procedures" section, ignoring:
   - Summary, Definitions, Clinical Indications, Procedures & Length of Stay
   - Continuation/Renewal/Reauthorization criteria
   - Repair/Revision/Conversion/Removal criteria (these are separate procedures, not "initial")
   - Experimental/Investigational sections
   - Billing codes, references, contraindications

2. **AND/OR detection from natural language**: The prompt must teach the LLM to detect operators from:
   - Explicit: "ALL of the following" = AND, "ONE/ANY of the following" = OR
   - Inline connectors: "; and" at end of item = AND with siblings, "; or" = OR with siblings
   - Implicit: numbered items with no connector default to AND (medical policy convention)
   - "MUST meet all" / "each of" / "both" = AND
   - "at least one" / "one or more" / "either" = OR
   - Mixed: "A and (B or C)" — nested operators

3. **Hierarchical rule_id generation**:
   - Root node is always "1"
   - Direct children: "1.1", "1.2", "1.3", etc.
   - Grandchildren: "1.1.1", "1.2.1", etc.
   - Map from PDF numbering (1/a/i/1) to dotted hierarchy

4. **Leaf vs non-leaf distinction**:
   - If an item has sub-items → it's a non-leaf node, MUST have `operator` and `rules` array
   - If an item has no sub-items → it's a leaf node, ONLY `rule_id` and `rule_text`
   - Never put `operator` or `rules` on a leaf node
   - Never omit `operator` or `rules` on a non-leaf node

5. **Edge cases the prompt must handle**:
   - Criteria that reference other sections ("see section below", "as defined above", "see CG009")
   - Inline exceptions ("EXCEPT when...", "unless...")
   - Very long criterion text that spans multiple lines/paragraphs
   - Items with notes or clarifications embedded (e.g., "Note: Enlargement of pouch...")
   - PDFs where the criteria section has no explicit "Initial" label — default to first criteria tree
   - PDFs with multiple indications (e.g., separate criteria for different drugs/procedures) — extract the primary/first one
   - Criteria that mix AND and OR within the same level (this should be split into nested nodes)

6. **Title extraction**: Extract the most descriptive title for the criteria tree (e.g., "Medical Necessity Criteria for Bariatric Surgery" not just "Bariatric Surgery")

### PART B: "INITIAL ONLY" DETECTION HEURISTICS

Give me a comprehensive Python implementation for detecting and extracting only the "Initial" criteria from PDF text. I need:

1. **Regex patterns and keyword lists** that identify:
   - Start of initial criteria: "Initial Criteria", "Initial Authorization", "Initial Approval", "Criteria for Medically Necessary", "Medical Necessity Criteria", "is considered medically necessary when"
   - End of initial criteria / start of continuation: "Continuation Criteria", "Continuation of Therapy", "Reauthorization", "Renewal Criteria", "Continued Authorization", "Ongoing Treatment"
   - Sections to SKIP entirely: "Repair", "Revision", "Conversion", "Removal", "Replacement", "Experimental", "Investigational", "Not Medically Necessary", "Contraindications", "Billing Codes", "CPT Codes", "HCPCS", "References", "Appendix"

2. **Section boundary detection algorithm**:
   - Step 1: Find ALL section headers in the extracted text
   - Step 2: Identify the "initial criteria" section (first criteria section, or explicitly labeled "Initial")
   - Step 3: Extract text from that section only, stopping at the next major section header
   - Step 4: Pass only that extracted section to the LLM

3. **Fallback logic**:
   - If no explicit "Initial"/"Continuation" labels exist → use the first "Criteria for Medically Necessary" section
   - If no clear criteria section exists → use the entire document but instruct LLM to find criteria
   - If multiple distinct criteria trees exist (e.g., for different indications) → take the first/primary one

4. **Confidence scoring**: How confident is the detection? Store this metadata so I can explain my approach in the Q&A.

### PART C: PDF TEXT EXTRACTION

Compare these Python PDF text extraction libraries for medical documents with complex formatting (numbered lists, tables, multi-column, special characters like ≥, ≤, ™):

1. **PyMuPDF (fitz)** — extraction quality, handling of list numbering, Unicode support, speed
2. **pdfplumber** — extraction quality, table handling, layout preservation
3. **PyPDF2/pypdf** — basic extraction capability
4. **pdfminer.six** — layout analysis capability

For each, give me:
- Code snippet to extract text from a PDF file
- How well it preserves the numbered/lettered/roman-numeral list structure
- How it handles special characters (≥, ≤, ™, em-dashes)
- Whether it preserves the order of content correctly
- Performance (speed for a ~10 page PDF)
- Which one YOU RECOMMEND for this specific use case and why

### PART D: JSON VALIDATION

Give me a complete Python implementation for validating the LLM output:

1. **JSON Schema** (jsonschema-compatible) that enforces:
   - Top level: title (string, required), insurance_name (string, required), rules (object, required)
   - rules node (recursive): rule_id (string, required), rule_text (string, required)
   - Non-leaf: operator (enum: "AND", "OR", required when rules present), rules (array, min 1 item, required when operator present)
   - Leaf: no operator, no rules
   - Consistency: if operator exists, rules must exist, and vice versa

2. **Custom validation functions** beyond schema:
   - rule_id hierarchy check: child rule_ids must be prefixed with parent rule_id (e.g., children of "1.2" must be "1.2.1", "1.2.2", etc.)
   - rule_id uniqueness check: no duplicate rule_ids in the entire tree
   - rule_id sequential check: siblings should be sequential (1.1, 1.2, 1.3 — not 1.1, 1.3, 1.7)
   - Depth check: warn if tree is deeper than 5 levels (likely LLM error)
   - Empty text check: no empty or whitespace-only rule_text values
   - Operator consistency: if parent says "ALL of the following" in rule_text, operator should be "AND"

3. **LLM output repair strategies**:
   - If LLM returns invalid JSON → try to fix with json_repair or regex cleanup
   - If LLM puts operator on leaf nodes → strip it
   - If LLM omits operator on non-leaf nodes → infer from rule_text ("all" → AND, "any" → OR, default AND)
   - If LLM returns flat list instead of tree → attempt to reconstruct hierarchy from rule_ids
   - If LLM returns the wrong section (continuation instead of initial) → detect and re-prompt
   - Maximum retry count: 3 attempts with increasingly explicit prompts

### PART E: OpenAI API INTEGRATION

Give me production-ready Python code for:

1. **API call with structured outputs / JSON mode**:
   - Using `response_format={"type": "json_object"}`
   - OR using OpenAI's function calling / structured outputs feature to enforce the schema
   - Which approach is more reliable for deeply nested recursive JSON? Why?

2. **Token management**:
   - Average Oscar guideline PDF is 5-15 pages. How many tokens is that roughly?
   - GPT-4o context window vs GPT-4o-mini — which should I use for cost vs quality?
   - If a PDF exceeds the context window, what chunking strategy should I use? (These are medical documents where the criteria section is typically 1-3 pages within a larger document — so pre-extracting the section should keep it within limits)
   - Cost estimate for processing 10-15 PDFs

3. **Error handling**:
   - Rate limit errors (429) — retry with backoff
   - Context length exceeded — truncate non-criteria sections
   - Malformed response — retry with more explicit prompt
   - Timeout — retry with shorter input

4. **Batch processing**:
   - Process 10+ PDFs efficiently
   - Track which ones succeeded/failed
   - Store LLM metadata (model name, prompt used, tokens consumed, latency)

Give me COMPLETE, copy-paste-ready code for all of the above. Not pseudocode — real Python I can run.
```

---

## PROMPT 3 — ChatGPT Deep Research: Full-Stack Architecture, Database, API, and React Tree UI

```
I am building a full-stack application in ~2 hours for a timed coding challenge. I need the most efficient possible architecture. Everything must work end-to-end: database, backend API, and frontend UI.

=== PROJECT REQUIREMENTS (EXACT) ===

BACKEND must:
1. Store ALL discovered medical guideline policies (50-100+ policies) with: title, pdf_url (UNIQUE), source_page_url, discovered_at
2. Store ALL download attempts with: policy_id (FK), stored_location (file path), downloaded_at, http_status, error (nullable)
3. Store AT LEAST 10 structured policies with: policy_id (FK), extracted_text, structured_json (the criteria tree), structured_at, llm_metadata (model name + prompt), validation_error (nullable)
4. Serve this data via API endpoints to the frontend
5. Be idempotent: re-running discovery/download must not create duplicate records

FRONTEND must:
1. Show a list/table of ALL discovered policies with: title, PDF link, indicator of whether it has a structured tree
2. For policies with structured trees, provide a detail view that:
   - Shows policy title + links (source page URL and PDF URL)
   - Renders the criteria as a NAVIGABLE TREE
   - Supports EXPAND/COLLAPSE per node
   - Clearly distinguishes AND operator nodes (e.g., blue), OR operator nodes (e.g., orange), and leaf criteria nodes (e.g., green or neutral)
   - Handles deeply nested trees (up to 5 levels deep, as seen in the real data)

=== THE STRUCTURED JSON I'M RENDERING ===

The tree is recursive. Here's the shape:
- Root: { title, insurance_name, rules: { rule_id, rule_text, operator, rules: [...children] } }
- Each node: { rule_id, rule_text } for leaves, or { rule_id, rule_text, operator: "AND"|"OR", rules: [...] } for branches
- Real trees have 3-5 levels of nesting
- Leaf nodes have medical criteria text that can be 1-3 sentences long
- Operator nodes have descriptive text like "Procedures are considered medically necessary when ALL of the following criteria are met"

=== WHAT I NEED YOU TO RESEARCH AND PROVIDE ===

### PART A: TECHNOLOGY STACK SELECTION (SPEED IS KING)

Evaluate these options and give me ONE definitive recommendation with justification:

**Backend:**
- FastAPI (Python) vs Flask vs Express.js (Node)
- For a 2-hour build, which has the least boilerplate to get CRUD API + DB working?
- Consider: I'm already using Python for the scraper and LLM pipeline, so Python backend means one language
- Do I even need a separate API server, or can I use Next.js API routes if I go with Next.js?

**Database:**
- SQLite vs PostgreSQL vs even just JSON files
- SQLite: zero setup, single file, great for demo — but any gotchas with concurrent access?
- PostgreSQL: more "production" but requires setup time I don't have
- For a 2-hour challenge being reviewed by engineers, what looks best without wasting setup time?
- Give me the exact ORM/library recommendation: SQLAlchemy, raw sqlite3, Prisma, Drizzle, etc.

**Frontend:**
- Next.js (App Router) vs Vite + React vs plain HTML/CSS/JS
- I need: routing (list page + detail page), API calls, tree rendering, expand/collapse state
- Which gets me there fastest?
- Should I use a component library (shadcn/ui, Chakra, MUI) or go plain Tailwind?

**Tree rendering:**
- What's the best approach for rendering a recursive JSON tree with expand/collapse in React?
- Options: react-d3-tree, react-treeview, custom recursive component, react-arborist, or something else?
- I need per-node expand/collapse, color-coded operators, and it should handle 50+ nodes gracefully
- Give me a comparison and your top pick with code example

### PART B: DATABASE SCHEMA (EXACT SQL)

Give me the complete CREATE TABLE statements. Requirements:
- `policies`: id (auto-increment PK), title (text not null), pdf_url (text unique not null), source_page_url (text not null), discovered_at (timestamp, default current)
- `downloads`: id (PK), policy_id (FK → policies.id), stored_location (text), downloaded_at (timestamp), http_status (integer), error (text nullable)
- `structured_policies`: id (PK), policy_id (FK → policies.id, unique — one structured tree per policy), extracted_text (text), structured_json (text/json), structured_at (timestamp), llm_model (text), llm_prompt (text), validation_error (text nullable)

Also give me:
- Indexes for common queries (list all policies, join with downloads, join with structured)
- The INSERT OR IGNORE / ON CONFLICT DO NOTHING patterns for idempotent inserts
- Migration script that creates tables if they don't exist (for clean setup)

For both SQLite and PostgreSQL so I can choose at implementation time.

### PART C: API DESIGN

Give me the complete API with exact routes, request/response shapes, and implementation code:

1. `GET /api/policies` — List all policies with download status and structured status
   - Response: array of { id, title, pdf_url, source_page_url, discovered_at, download_status: "success"|"failed"|"pending", has_structured_tree: boolean }
   - Should be a single SQL query with LEFT JOINs, not N+1

2. `GET /api/policies/:id` — Get single policy detail
   - Response: full policy + download info + structured_json if available
   - Include the complete tree in the response

3. `GET /api/policies/:id/tree` — Get just the structured tree
   - Response: the JSON tree directly (for rendering)

4. `GET /api/stats` — Dashboard stats (nice to have)
   - Total policies, total downloaded, total structured, total failed

Give me the full implementation in your recommended framework with proper error handling, CORS configuration, and database connection management.

### PART D: FRONTEND IMPLEMENTATION

Give me complete, production-quality React components:

**1. PolicyListPage component:**
- Fetches and displays all policies in a table/list
- Columns: Title (clickable → detail page), PDF URL (external link), Status badge (Downloaded/Failed/Pending), Structured badge (yes/no, clickable if yes)
- Search/filter by title (nice to have)
- Responsive layout
- Loading and error states

**2. PolicyDetailPage component:**
- Route: /policy/:id
- Shows: title, source page link, PDF link (opens in new tab), download status
- If structured tree exists: renders the TreeViewer component below
- If no structured tree: shows message "No structured criteria available"

**3. TreeViewer component (THE CRITICAL ONE):**

I need a recursive React component that renders the JSON criteria tree. Specific requirements:

a) **Visual hierarchy**: Each nesting level should be indented. Use connecting lines or visual nesting cues so the user understands parent-child relationships.

b) **Expand/collapse**: Each non-leaf node should have a toggle button (▶/▼ or +/-). Clicking it shows/hides all children. Default state: expand first 2 levels, collapse deeper levels.

c) **Operator styling**:
   - AND nodes: distinct color (e.g., blue badge/pill saying "AND")
   - OR nodes: distinct color (e.g., orange badge/pill saying "OR")
   - The operator badge should be immediately visible next to the node text

d) **Leaf styling**: Leaf criteria should look different from operator nodes (e.g., no badge, just the criterion text with a bullet or checkbox icon)

e) **Rule ID display**: Show rule_id as a small label (e.g., "1.2.3") next to each node

f) **Long text handling**: Medical criteria can be long (2-3 sentences). Text should wrap cleanly, not overflow.

g) **Expand All / Collapse All buttons**: At the top of the tree

h) **Node count**: Show how many children a collapsed node has (e.g., "▶ 1.4 Pre-operative plan (AND, 7 criteria)")

Give me the complete component code with TypeScript, Tailwind CSS styling, and all the interactive features above. Make it look professional — this is being reviewed by engineers.

**4. Layout/Navigation:**
- Simple layout: header with title, main content area
- Two routes: / (list) and /policy/:id (detail)
- Back button from detail to list

### PART E: PROJECT STRUCTURE

Give me the exact folder structure for the entire project. It should be clean and organized:

```
oscar-guidelines/
├── backend/         (Python: scraper + LLM pipeline + API)
├── frontend/        (React app)
├── data/            (downloaded PDFs, SQLite DB)
├── .env.example
├── README.md
└── ...
```

Fill in EVERY file and subfolder. Tell me what goes in each file.

### PART F: SETUP & RUN INSTRUCTIONS

Give me the exact commands to:
1. Install all dependencies (Python + Node)
2. Initialize the database
3. Run the scraper (discovery + download)
4. Run the LLM structuring pipeline
5. Start the API server
6. Start the frontend dev server
7. Open the app in a browser

These should be copy-paste-ready. Include a Makefile or script if it makes things easier.

### PART G: IMPLEMENTATION ORDER (2-HOUR BATTLE PLAN)

Give me a minute-by-minute implementation plan optimized for the 2-hour timebox:

Phase 1 (0-30 min): What to build first and why
Phase 2 (30-60 min): What comes next
Phase 3 (60-90 min): Core features that MUST be done
Phase 4 (90-120 min): Polish and what to cut if behind

What's the MINIMUM VIABLE version I can demo if I only finish 60% of the work?
What should I cut first if I'm running out of time?
What should I absolutely NOT cut (deal-breakers for the review)?

### PART H: Q&A PREPARATION

The 30-minute Q&A will cover these topics. For each, give me talking points and potential follow-up questions with strong answers:

1. **PDF discovery completeness**: "How did you ensure you found ALL PDFs?"
   - How to verify count, handle pagination, detect missing links

2. **Retries, throttling, idempotency**: "How do you handle failures and re-runs?"
   - Exponential backoff, rate limiting, UPSERT patterns, duplicate detection

3. **Initial-only selection logic**: "How do you detect 'initial' vs 'continuation' criteria?"
   - My heuristic, its failure modes, what I'd improve with more time

4. **LLM output validation**: "How do you handle malformed JSON from the LLM?"
   - Schema validation, retry logic, repair strategies, error persistence

5. **Tree rendering for large nested criteria**: "How does your UI handle deeply nested trees?"
   - Recursive components, expand/collapse, performance considerations, accessibility

Give me concise but impressive answers for each that show depth of thinking.
```

---

## USAGE INSTRUCTIONS

| Prompt | Send to | Purpose | Priority |
|--------|---------|---------|----------|
| **Prompt 1** | ChatGPT Deep Research | Site reconnaissance — page structure, PDF URLs, anti-scraping, complete guideline inventory | **Run first** — blocks scraper implementation |
| **Prompt 2** | Gemini Deep Research | LLM pipeline — prompts, initial-only detection, PDF extraction, JSON validation, OpenAI integration | **Run in parallel with Prompt 1** — blocks structuring pipeline |
| **Prompt 3** | ChatGPT Deep Research | Full-stack architecture — DB, API, UI components, project structure, implementation order | **Run in parallel** — blocks all coding |

All three should be submitted simultaneously. Results from all three combine into everything needed to implement the complete project.
