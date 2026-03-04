"""
BEAD INTERFACES — Contracts between autonomous work units.

Each function signature here is the contract. Implementations can be swapped
when deep research results come back without touching other beads.

Drop-in upgrade points marked with 🔌
"""

from typing import Optional, Protocol
from dataclasses import dataclass


# ── Data Types ──────────────────────────────────────────────────────────

@dataclass
class DiscoveredPolicy:
    title: str
    pdf_url: str
    source_page_url: str


@dataclass
class DownloadResult:
    policy_id: int
    stored_location: str
    http_status: int
    error: Optional[str] = None


@dataclass
class ExtractionResult:
    text: str
    page_count: int


@dataclass
class StructuringResult:
    structured_json: dict
    llm_metadata: dict  # model name, prompt hash, tokens used
    validation_error: Optional[str] = None


# ── Bead Interfaces (Protocols) ─────────────────────────────────────────

class IDiscoverer(Protocol):
    """B2: PDF Discovery — scrape source page for all guideline PDF URLs.

    🔌 UPGRADE POINTS (from research):
    - Scraping strategy (requests+BS4 vs Playwright vs Selenium)
    - Source page structure (does it use JS rendering?)
    - URL patterns for individual policy pages
    - How to find the actual PDF download link on each policy page
    """

    async def discover(self) -> list[DiscoveredPolicy]:
        """Returns all discovered policies from the Oscar source page."""
        ...


class IDownloader(Protocol):
    """B3: PDF Downloader — download all discovered PDFs.

    🔌 UPGRADE POINTS (from research):
    - Rate limiting strategy (fixed delay vs adaptive)
    - Retry config (attempts, backoff multiplier)
    - Whether Oscar blocks/throttles and how to handle
    - Concurrent downloads or sequential
    """

    async def download(self, policy_id: int, pdf_url: str, dest_dir: str) -> DownloadResult:
        """Downloads a single PDF. Returns result with status."""
        ...

    async def download_all(self, policies: list[dict], dest_dir: str) -> list[DownloadResult]:
        """Downloads all PDFs with rate limiting. Returns results."""
        ...


class ITextExtractor(Protocol):
    """B5: PDF Text Extractor — extract clean text from PDF files.

    🔌 UPGRADE POINTS (from research):
    - Best library (PyMuPDF vs pdfplumber vs pdfminer)
    - How to preserve list numbering and hierarchy
    - Header/footer stripping strategy
    - Table handling if any PDFs have tables
    """

    def extract(self, pdf_path: str) -> ExtractionResult:
        """Extracts text from a PDF file."""
        ...


class IStructurer(Protocol):
    """B6: LLM Structuring Pipeline — convert text to JSON tree.

    🔌 UPGRADE POINTS (from research):
    - Optimal system prompt (grounded in PDF structure analysis)
    - Initial-only detection heuristic (keywords, section headers, fallback)
    - OpenAI model choice (gpt-4o vs gpt-4o-mini for cost)
    - Structured outputs vs function calling vs raw JSON
    - Token management for large PDFs (chunking strategy)
    - Few-shot examples beyond oscar.json
    """

    async def structure(self, extracted_text: str, policy_title: str) -> StructuringResult:
        """Structures extracted text into oscar.json format."""
        ...


class IValidator(Protocol):
    """B7: JSON Schema Validator — validate LLM output.

    🔌 UPGRADE POINTS (from research):
    - Additional validation rules beyond schema (e.g. rule_id format)
    - Auto-repair strategies for common LLM mistakes
    """

    def validate(self, data: dict) -> tuple[bool, Optional[str]]:
        """Validates structured JSON. Returns (is_valid, error_message)."""
        ...


# ── Pipeline Orchestrator ───────────────────────────────────────────────

class IPipeline(Protocol):
    """Full pipeline: discover → download → extract → structure → validate → store.

    This is the top-level orchestrator that wires all beads together.
    """

    async def run_discovery(self) -> int:
        """Discover and store all policies. Returns count."""
        ...

    async def run_downloads(self) -> dict:
        """Download all PDFs. Returns {success: N, failed: N}."""
        ...

    async def run_structuring(self, limit: int = 10) -> dict:
        """Structure at least `limit` policies. Returns {success: N, failed: N}."""
        ...

    async def run_full(self) -> dict:
        """Run entire pipeline end-to-end."""
        ...
