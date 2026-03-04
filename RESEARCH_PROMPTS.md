# Research Prompts for Oscar Medical Guidelines Project

## Prompt 1 — ChatGPT Deep Research: Oscar Page Structure & Scraping Strategy

```
I need to build a scraper that discovers and downloads ALL medical guideline PDFs from this page:
https://www.hioscar.com/clinical-guidelines/medical

Please do deep research on the following:

1. **Page structure**: Visit https://www.hioscar.com/clinical-guidelines/medical and analyze:
   - How are the guideline links structured? Are they direct PDF links or do they link to intermediate pages (like https://www.hioscar.com/medical/cg013v11) that then contain PDF links/embedded PDFs?
   - What is the full URL pattern for guideline pages and PDFs? (e.g., /medical/cgXXXvYY)
   - How many total guidelines are listed?
   - Is the page statically rendered HTML or does it load content dynamically via JavaScript/API calls?
   - Are there pagination, tabs, or "load more" buttons?
   - What are the link text patterns (used to extract policy titles)?

2. **PDF access**: For a few example guideline pages (like cg013v11):
   - Is the PDF embedded in the page, linked directly, or served through a viewer?
   - What is the actual PDF download URL pattern?
   - Are there any authentication walls, cookie requirements, or redirects?
   - What Content-Type and headers does the PDF response return?

3. **Rate limiting & bot protection**:
   - Does the site use Cloudflare, reCAPTCHA, or any bot detection?
   - What User-Agent or headers are needed?
   - Any robots.txt restrictions for these paths?
   - What's a safe crawl delay?

4. **PDF content structure** (look at a few actual guideline PDFs):
   - How is the text structured inside the PDFs?
   - How are "Initial" vs "Continuation" criteria sections labeled/formatted?
   - How are the criteria lists formatted (numbered, bulleted, nested)?
   - What keywords/headings mark the start of "Initial Criteria" vs "Continuation Criteria"?
   - Are there PDFs with multiple distinct criteria trees (multiple indications)?

Give me concrete findings with actual URLs, HTML snippets, and examples so I can implement a Python scraper using requests + BeautifulSoup (or Playwright if JS rendering is needed).
```

---

## Prompt 2 — Gemini Deep Research: LLM Prompt Engineering for Criteria → JSON Tree Extraction

```
I'm building a pipeline that takes extracted text from Oscar Health medical guideline PDFs and uses an LLM (GPT-4o or similar) to structure the "Initial" medical necessity criteria into a JSON decision tree.

Here is the EXACT target JSON schema (example for Bariatric Surgery):

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
                    {"rule_id": "1.2.1", "rule_text": "Body mass index (BMI) ≥40"},
                    {
                        "rule_id": "1.2.2",
                        "rule_text": "BMI greater ≥35 with ONE of the following severe obesity-related comorbidities",
                        "operator": "OR",
                        "rules": [
                            {"rule_id": "1.2.2.1", "rule_text": "Clinically significant cardio-pulmonary disease..."},
                            {"rule_id": "1.2.2.2", "rule_text": "Coronary artery disease..."}
                        ]
                    }
                ]
            }
        ]
    }
}

Rules:
- Top level has: title (string), insurance_name (always "Oscar Health"), rules (root node object)
- Each node has: rule_id (hierarchical like "1", "1.1", "1.2.1"), rule_text (string)
- Non-leaf nodes ALSO have: operator ("AND" or "OR"), rules (array of child nodes)
- Leaf nodes have ONLY rule_id and rule_text (no operator, no rules array)
- The operator is determined by the language: "all of the following" = AND, "any/one of the following" = OR

I need help with:

1. **The optimal LLM system prompt and user prompt** to reliably convert raw PDF text into this exact JSON structure. The prompt must:
   - Instruct the LLM to ONLY extract the "Initial" criteria section (not "Continuation" criteria)
   - Handle PDFs that have multiple indication sections (e.g., separate criteria for different procedures) — pick the first/primary initial criteria tree
   - Correctly identify AND vs OR logic from natural language cues ("all of", "each of", "must meet all" = AND; "any of", "one or more of", "at least one" = OR)
   - Produce hierarchical rule_id numbering (1 → 1.1 → 1.1.1)
   - Handle edge cases: nested conditions, exceptions/exclusions within criteria, criteria that reference other sections

2. **Detection heuristics for "Initial" vs "Continuation"**: What text patterns reliably distinguish initial criteria from continuation criteria in medical policy documents? Give me regex patterns or keyword lists I can use to:
   - Find the "Initial" section boundaries in extracted PDF text
   - Detect when a PDF has both Initial and Continuation sections
   - Fallback: if no clear Initial/Continuation split, take the first complete criteria tree

3. **JSON validation strategy**: How should I validate the LLM output?
   - A JSON schema definition that enforces the recursive node structure
   - Validation rules: rule_ids must be hierarchical and unique, operators only on non-leaf nodes, leaf nodes must not have rules array
   - Common LLM failure modes and how to detect/fix them (e.g., missing operators, flat instead of nested structure, hallucinated criteria)

4. **Prompt for handling specific difficult patterns** seen in medical policies:
   - "Member must meet criteria A AND (B OR C)"
   - "All of the following EXCEPT when..."
   - Numbered lists with sub-bullets
   - Criteria that say "see above" or reference other sections
   - Multiple distinct procedures each with their own criteria tree in one PDF

Give me copy-paste-ready prompts, a JSON schema, and validation code in Python.
```

---

## Prompt 3 — ChatGPT: Full-Stack Implementation Architecture & Code

```
I'm building this project in ~2 hours. It needs:

BACKEND:
- Python scraper: discover PDF links from https://www.hioscar.com/clinical-guidelines/medical, download all PDFs, extract text, send to LLM, validate JSON output, store everything in DB
- Database with 3 tables: policies (all discovered), downloads (all download attempts), structured_policies (at least 10 with JSON trees)
- API endpoints to serve data to the frontend

FRONTEND:
- List all policies (title + PDF link + whether it has a structured tree)
- Detail view: render the JSON criteria tree with expand/collapse, clearly showing AND/OR operators vs leaf nodes

Constraints:
- Must be fast to implement (2 hour timebox)
- Idempotent reruns (no duplicate records)
- Polite scraping (throttling, retries)
- Error visibility (logged + persisted)

Please give me a COMPLETE implementation plan with:

1. **Recommended stack** (fastest to implement):
   - Backend: FastAPI or Flask? SQLite or Postgres?
   - PDF text extraction: PyMuPDF (fitz) vs pdfplumber vs PyPDF2 — which is most reliable for medical documents with complex formatting?
   - Frontend: Next.js, plain React, or something simpler?
   - Tree rendering: best React library or approach for recursive expand/collapse trees with AND/OR node styling?

2. **Database schema**: Give me the exact SQLite (or Postgres) CREATE TABLE statements for:
   - policies (id, title, pdf_url UNIQUE, source_page_url, discovered_at)
   - downloads (id, policy_id FK, stored_location, downloaded_at, http_status, error)
   - structured_policies (id, policy_id FK, extracted_text, structured_json, structured_at, llm_model, llm_prompt, validation_error)

3. **Project structure**: Exact folder/file layout

4. **Scraper implementation details**:
   - How to handle the Oscar website (static HTML vs JS-rendered)
   - Rate limiting approach (simple sleep between requests vs token bucket)
   - Retry logic (exponential backoff, max retries)
   - Idempotency (INSERT OR IGNORE / ON CONFLICT DO NOTHING)

5. **LLM pipeline details**:
   - OpenAI API call with structured output / function calling vs raw JSON parsing
   - How to use GPT-4o's JSON mode or response_format
   - Token management for long PDF texts (chunking strategy if needed)
   - Cost estimate for processing 10+ PDFs

6. **UI component architecture**:
   - Policy list component with structured/unstructured indicators
   - Tree viewer component: recursive React component with expand/collapse state
   - How to style AND nodes (e.g., blue) vs OR nodes (e.g., orange) vs leaf nodes
   - Responsive layout considerations

7. **Step-by-step implementation order** (what to build first to last, optimized for the 2-hour timebox):
   - Phase 1: DB + scraper (discovery + download)
   - Phase 2: LLM pipeline (extract + structure + validate)
   - Phase 3: API + UI
   - What to cut if running out of time

Give me concrete code snippets, not just descriptions. I want to be able to copy-paste and adapt.
```
