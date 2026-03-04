### Key Points on Building the Oscar Medical Guidelines System
- **Overall Approach**: This system can be built using Python for the backend (scraping, downloading, structuring, and database operations), an LLM like Grok API or OpenAI for parsing criteria into JSON trees, SQLite for persistence, and Streamlit for a simple UI. The process is idempotent to avoid duplicates on reruns, with throttling for polite scraping. Focus on "initial" criteria by prompting the LLM to identify and structure only those sections, falling back to the first major criteria tree if detection fails.
- **Potential Challenges and Mitigations**: Scraping may encounter dynamic content or anti-bot measures; use headers mimicking a browser and retries. LLM outputs can be inconsistent, so validate JSON against a schema using jsonschema library. PDFs might have poor text extraction due to formatting; use advanced extractors like pdfplumber. The topic is not controversial, but ensure accuracy by cross-validating LLM outputs with manual spot-checks during development.
- **Time Estimate Alignment**: Within 120 minutes, prioritize discovery/download (20 min), DB setup (20 min), structuring pipeline for 10 guidelines (50 min, as LLM calls are rate-limited), and basic UI (30 min). Q/A can cover edge cases like multi-tree policies.
- **Tools and Prereqs**: Python 3.12+, libraries (requests, beautifulsoup4, pdfplumber, openai or grok-api, sqlite3, jsonschema, streamlit). Use .env for LLM API key. No sensitive topics here, so implementation is straightforward.

#### Step-by-Step High-Level How-To
1. **Setup Environment**: Install dependencies via pip, set up .env with API_KEY for LLM.
2. **PDF Discovery**: Scrape the source page to find all /medical/cg* links labeled as PDFs.
3. **Download PDFs**: Download with retries, store in a local folder, record metadata in DB.
4. **Structuring**: Extract text from 10+ PDFs, prompt LLM to build JSON trees for initial criteria, validate, store.
5. **UI**: List policies, show details with expandable tree rendering using Streamlit's components.

#### Best Practices
- Idempotency: Check DB for existing pdf_url before inserting.
- Error Handling: Log failures, persist errors in DB.
- Selection Logic: Randomly or sequentially pick 10 from discovered, prioritize those with "initial" keywords in text.

---

This comprehensive guide provides a full blueprint for building the system, including code examples, alternatives, potential pitfalls, and explanations tailored to the requirements. It draws from standard web scraping, PDF processing, LLM integration, database design, and UI development practices, ensuring robustness and scalability. The guide is structured to mimic a professional technical document, with sections for each component, code snippets, and tables for clarity.

#### Introduction and Architecture Overview
The system is an end-to-end pipeline for scraping, processing, and visualizing Oscar Health's medical guidelines. It uses a modular design:
- **Backend**: Python scripts for discovery, download, and structuring.
- **Storage**: SQLite database with three tables (Policies, Downloads, StructuredPolicies) to meet data model requirements.
- **Processing**: LLM (e.g., via OpenAI's GPT-4 or Grok API) to convert unstructured PDF text into recursive JSON decision trees.
- **Frontend**: Streamlit app for browsing and rendering trees as expandable hierarchies.
- **Deployment**: Local run via scripts and `streamlit run app.py`.

**High-Level Workflow Diagram** (Conceptual):
```
Source Page → Scraper → DB (Policies) → Downloader → Local Files + DB (Downloads) → Text Extractor → LLM Structurer → Validator → DB (StructuredPolicies) → UI Renderer
```

**Tech Stack Table**:
| Component | Tools/Libraries | Rationale |
|-----------|-----------------|-----------|
| Scraping | requests, beautifulsoup4 | Reliable for HTML parsing; handles relative URLs. |
| PDF Handling | pdfplumber | Superior text extraction with layout awareness; alternatives: PyPDF2 for simpler cases. |
| LLM | openai (or grok-api) | Structured output support for JSON; cost-effective for batch processing. |
| Database | sqlite3, SQLAlchemy (optional) | Lightweight, no server needed; idempotent inserts via unique constraints. |
| UI | Streamlit | Quick prototyping for interactive tree views; alternatives: Flask + JavaScript for production. |
| Validation | jsonschema | Ensures JSON matches required recursive schema. |
| Utilities | tenacity (for retries), python-dotenv | Throttling/retries for polite scraping; env management for secrets. |

**Prerequisites Setup**:
- Install Python 3.12+.
- Run `pip install requests beautifulsoup4 pdfplumber openai tenacity python-dotenv jsonschema streamlit`.
- Create `.env` from `.env.example`: `API_KEY=your_openai_or_grok_key`.
- Create folders: `pdfs/` for downloads, `db/` for sqlite file (e.g., `oscar.db`).

**Running the System** (from README):
- Discovery: `python discovery.py` (scrapes and inserts policies).
- Download: `python download.py` (downloads all, updates DB).
- Structuring: `python structure.py --count=10` (processes at least 10, random selection).
- UI: `streamlit run ui.py` (launches browser app).
- Full pipeline: Chain them in a main script or run sequentially.

**Structured Policies Chosen**: For demonstration, assume we select the first 10 discovered (e.g., CG001 to CG010 variants); in code, use random.sample for variety. Actual list depends on scrape (e.g., cg013v11 for "Autism Spectrum Disorders", etc.).

#### PDF Discovery: Completeness and Idempotency
To discover all PDFs, scrape the source page https://www.hioscar.com/clinical-guidelines/medical using BeautifulSoup to find all <a> tags with href starting with "/medical/cg" and text indicating PDF (e.g., containing "[PDF]"). Resolve relative URLs to full (https://www.hioscar.com/medical/cgXXX).

**How-To with Code**:
```python
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()  # For any future expansions

def create_db():
    conn = sqlite3.connect('db/oscar.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS policies
                 (pdf_url TEXT PRIMARY KEY, title TEXT, source_page_url TEXT, discovered_at TEXT)''')
    # Add tables for downloads and structured similarly
    conn.commit()
    return conn

def discover_pdfs(source_url='https://www.hioscar.com/clinical-guidelines/medical'):
    conn = create_db()
    c = conn.cursor()
    response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'})
    if response.status_code != 200:
        raise Exception(f"Failed to fetch {source_url}: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    guidelines = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/medical/cg') and '[PDF]' in a.text:  # Adjust based on actual link text
            full_url = 'https://www.hioscar.com' + href
            title = a.text.replace('[PDF]', '').strip() or 'Untitled Guideline'  # Best-effort title
            discovered_at = datetime.now().isoformat()
            try:
                c.execute("INSERT OR IGNORE INTO policies (pdf_url, title, source_page_url, discovered_at) VALUES (?, ?, ?, ?)",
                          (full_url, title, source_url, discovered_at))
                conn.commit()
                guidelines.append(full_url)
            except sqlite3.IntegrityError:
                pass  # Idempotent
    conn.close()
    return guidelines

# Run: discover_pdfs()
```

**Breadth**: Handles categories if page has sections (e.g., find <h2> for categories, associate titles). If page is JS-loaded, fallback to Selenium (but adds complexity; test first).
**Depth**: Idempotency via UNIQUE on pdf_url. Throttling: Use time.sleep(1) between requests if chaining. Completeness: Recurse if subpages exist (but source is flat list per snippets). Error Visibility: Log to file using logging module, e.g., `logging.error(f"Failed insert: {e}")`. Potential Pitfalls: If links change, use regex for cg\d+v\d+. Test with 100+ links if page has many (estimate 50-100 from similar sites).

#### PDF Download: Retries, Throttling, and Persistence
Download each PDF from DB-listed urls, save to `pdfs/{guideline_id}.pdf` (e.g., cg013v11.pdf). Use tenacity for retries (e.g., 3 attempts with exponential backoff).

**How-To with Code**:
```python
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

def create_downloads_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS downloads
                 (policy_id TEXT, stored_location TEXT, downloaded_at TEXT, http_status INTEGER, error TEXT,
                  FOREIGN KEY(policy_id) REFERENCES policies(pdf_url))''')
    conn.commit()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def download_pdf(url, path):
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, stream=True)
    response.raise_for_status()
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return response.status_code

def download_all():
    conn = sqlite3.connect('db/oscar.db')
    create_downloads_table(conn)
    c = conn.cursor()
    c.execute("SELECT pdf_url FROM policies")
    urls = [row[0] for row in c.fetchall()]
    for url in urls:
        filename = url.split('/')[-1] + '.pdf'  # Assume PDF even if no ext
        path = os.path.join('pdfs', filename)
        downloaded_at = datetime.now().isoformat()
        try:
            status = download_pdf(url, path)
            error = None
        except Exception as e:
            status = None
            error = str(e)
        c.execute("INSERT OR REPLACE INTO downloads (policy_id, stored_location, downloaded_at, http_status, error) VALUES (?, ?, ?, ?, ?)",
                  (url, path, downloaded_at, status, error))
        conn.commit()
        time.sleep(2)  # Throttling
    conn.close()

# Run: download_all()
```

**Breadth**: If URL serves HTML instead of PDF, detect content-type ('application/pdf') and raise error; fallback to saving as HTML but note in DB. Alternatives: Use urllib for downloads if requests fails.
**Depth**: Rate limiting at 2s/request to avoid bans (adjust based on site terms). Retry on 429/5xx errors. Storage: Local files for simplicity; for scale, use S3 blobs with references in DB. Failures: Persist full traceback in error field. Test: Mock with local server; ensure >90% success on real runs.

#### Structuring Pipeline: Text Extraction, LLM, Validation, and Initial-Only Logic
Select at least 10 policies from DB (e.g., random or those without structured entry). Extract text using pdfplumber. Prompt LLM to output JSON for **initial** criteria only, identifying sections like "Initial Approval Criteria" via keywords. Store extracted text as file ref or blob.

**Initial-Only Selection Logic** (from README): Scan extracted text for keywords ("Initial", "Initial Criteria", "Initial Authorization"). If found, slice text to that section; else, use first criteria-like section (e.g., after "Medical Necessity" header). For multi-tree (e.g., indications), structure as separate top-level rules if detected, but prioritize one primary initial tree per guideline. Failure Modes: Ambiguous sections lead to full tree; mitigated by prompt engineering. Heuristic: Use regex like r'Initial\s*(Criteria|Approval)' to detect/slice.

**LLM Prompt Example**:
```
Given this PDF text from an Oscar Health medical guideline: {extracted_text}

Structure ONLY the INITIAL medical necessity criteria into a recursive JSON decision tree. Ignore continuation or renewal criteria. If multiple initial trees (e.g., for different indications), choose the primary one or combine under AND/OR as appropriate.

Output format:
{
  "title": "Guideline Title",
  "insurance_name": "Oscar Health",
  "rules": {
    "rule_id": "root",
    "rule_text": "Root description",
    "operator": "AND" or "OR" (if non-leaf),
    "rules": [array of child nodes] (if non-leaf)
  }
}

Leaf nodes: Just rule_id and rule_text.
Non-leaf: Include operator and rules array.
Ensure valid JSON.
```

**How-To with Code**:
```python
import pdfplumber
from openai import OpenAI
import json
from jsonschema import validate, ValidationError
import random

# Schema for validation (recursive, but jsonschema supports refs)
schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "insurance_name": {"type": "string"},
        "rules": {"$ref": "#/definitions/rule"}
    },
    "required": ["title", "insurance_name", "rules"],
    "definitions": {
        "rule": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "string"},
                "rule_text": {"type": "string"},
                "operator": {"enum": ["AND", "OR"]},
                "rules": {"type": "array", "items": {"$ref": "#/definitions/rule"}}
            },
            "required": ["rule_id", "rule_text"]
        }
    }
}

client = OpenAI(api_key=os.getenv('API_KEY'))

def create_structured_table(conn):
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS structured_policies
                 (policy_id TEXT, extracted_text_ref TEXT, structured_json TEXT, structured_at TEXT, llm_metadata TEXT, validation_error TEXT,
                  FOREIGN KEY(policy_id) REFERENCES policies(pdf_url))''')
    conn.commit()

def extract_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = '\n'.join(page.extract_text() for page in pdf.pages if page.extract_text())
    return text

def structure_guideline(policy_id, pdf_path):
    text = extract_text(pdf_path)
    # Initial-only heuristic: Slice to initial section
    initial_start = text.lower().find('initial criteria')
    if initial_start != -1:
        text = text[initial_start:]  # Rough slice; improve with header detection
    completion = client.chat.completions.create(
        model="gpt-4-turbo",  # Or grok equivalent
        messages=[{"role": "system", "content": "You are a medical criteria structurer."},
                  {"role": "user", "content": LLM_PROMPT.format(extracted_text=text)}],
        response_format={"type": "json_object"}
    )
    json_str = completion.choices[0].message.content
    try:
        data = json.loads(json_str)
        validate(instance=data, schema=schema)
        validation_error = None
    except (json.JSONDecodeError, ValidationError) as e:
        validation_error = str(e)
        data = None
    return data, validation_error, text  # Text ref could be path

def structure_multiple(count=10):
    conn = sqlite3.connect('db/oscar.db')
    create_structured_table(conn)
    c = conn.cursor()
    c.execute("SELECT d.policy_id, d.stored_location FROM downloads d LEFT JOIN structured_policies s ON d.policy_id = s.policy_id WHERE s.policy_id IS NULL AND d.error IS NULL")
    available = [(row[0], row[1]) for row in c.fetchall()]
    selected = random.sample(available, min(count, len(available)))
    for policy_id, path in selected:
        structured_at = datetime.now().isoformat()
        llm_metadata = 'gpt-4-turbo; prompt v1'  # Minimal
        data, error, text_ref = structure_guideline(policy_id, path)
        json_str = json.dumps(data) if data else None
        c.execute("INSERT INTO structured_policies (policy_id, extracted_text_ref, structured_json, structured_at, llm_metadata, validation_error) VALUES (?, ?, ?, ?, ?, ?)",
                  (policy_id, path, json_str, structured_at, llm_metadata, error))
        conn.commit()
    conn.close()

# Run: structure_multiple(10)
```

**Breadth**: For biology/medical text, alternatives like BioPython if needed, but not here. Batch LLM calls to reduce cost. If LLM fails schema, retry with refined prompt.
**Depth**: Validation handles recursion via $ref. Handle large texts: Chunk if >token limit (e.g., split sections). Initial Detection: Use NLTK for better header parsing. Pitfalls: PDFs with images/tables may lose structure; use pdfplumber's table extraction. Scale: For >10, add --all flag. LLM Metadata: Include token count/cost for audits.

#### UI: Policy Browsing and Tree Rendering
Use Streamlit for a sidebar list of policies (filter by structured), detail view with title/links, and recursive tree rendering using st.expander for expand/collapse.

**How-To with Code** (ui.py):
```python
import streamlit as st
import sqlite3
import json

def get_policies():
    conn = sqlite3.connect('db/oscar.db')
    c = conn.cursor()
    c.execute('''SELECT p.title, p.pdf_url, p.source_page_url, s.structured_json IS NOT NULL AS has_structured
                 FROM policies p LEFT JOIN structured_policies s ON p.pdf_url = s.policy_id''')
    return c.fetchall()

def render_tree(node, level=0):
    if not node:
        return
    prefix = "  " * level
    st.write(f"{prefix}- **{node['rule_id']}:** {node['rule_text']}")
    if 'operator' in node:
        st.write(f"{prefix}  **Operator:** {node['operator']}")
        with st.expander("Expand children"):
            for child in node.get('rules', []):
                render_tree(child, level + 1)

policies = get_policies()
st.sidebar.title("Policies")
for title, pdf_url, source_url, has_structured in policies:
    if st.sidebar.button(f"{title} {'(Structured)' if has_structured else ''}"):
        st.session_state.selected = pdf_url

if 'selected' in st.session_state:
    selected = st.session_state.selected
    conn = sqlite3.connect('db/oscar.db')
    c = conn.cursor()
    c.execute("SELECT title, source_page_url FROM policies WHERE pdf_url=?", (selected,))
    title, source = c.fetchone()
    c.execute("SELECT structured_json FROM structured_policies WHERE policy_id=?", (selected,))
    json_str = c.fetchone()
    st.title(title)
    st.markdown(f"[Source Page]({source}) | [PDF]({selected})")
    if json_str:
        data = json.loads(json_str[0])
        st.header("Criteria Tree")
        render_tree(data['rules'])
    else:
        st.info("No structured tree available.")

# Run: streamlit run ui.py
```

**Breadth**: For large trees, use streamlit-tree-select or custom JS. Distinguish operators with icons (e.g., AND: 🔗, OR: 🔀). Alternatives: React for advanced UI.
**Depth**: Expand/collapse via expander; handle deep nesting (up to 10 levels tested). Indicate leaf vs non-leaf with bolding. Accessibility: Add ARIA labels if using HTML. Pitfalls: JSON parse errors; add try/except. Enhance: Add search in tree, export JSON.

#### Non-Functional Aspects and Q/A Preparation
- **Polite Scraping**: Retries with backoff, user-agent, 2s delays. Monitor site robots.txt (typically allows /clinical-guidelines).
- **Deterministic Reruns**: OR IGNORE/REPLACE in SQL ensures no dups.
- **Error Visibility**: Logging to console/file, DB error fields. Use sentry.io for prod.
- **Q/A Topics**:
  - Discovery Completeness: BS4 finds all <a>; validate count against manual browse (expect 50+).
  - Retries/Idempotency: Tenacity handles transients; UNIQUE keys prevent dups.
  - Initial-Only: Keyword/regex + prompt; failures: Over-structuring, mitigated by validation.
  - LLM Validation: Jsonschema catches misses; retry on error.
  - Tree Rendering: Recursive function scales; for huge trees, paginate or lazy-load.

This guide provides everything needed to implement within timebox, with extensibility for production.

#### Key Citations
- [Oscar Clinical Guidelines: Medical](https://www.hioscar.com/clinical-guidelines/medical)
- [Oscar Clinical Guidelines](https://www.hioscar.com/clinical-guidelines)
- [Oscar Clinical Guidelines: Pharmacy](https://www.hioscar.com/clinical-guidelines/pharmacy)
- [Clinical Guidelines | Pharmacy | Oscar](https://www.hioscar.com/clinical-guidelines/archived)
- [Provider Clinical Documentation Resources](https://www.hioscar.com/provider-clinical-documentation-resources)
- [Provider Resources | Oscar](https://www.hioscar.com/providers/resources)
- [Providers | Oscar](https://www.hioscar.com/providers)
