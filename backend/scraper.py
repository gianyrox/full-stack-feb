"""
B2: PDF Discovery + B3: PDF Resolver & Downloader

Two-phase pipeline:
  1. Discover intermediate policy page URLs from the Oscar listing page
  2. Resolve each to a real PDF URL (via __NEXT_DATA__) and download

Based on ChatGPT deep research findings (research/1chatgpt.md).
"""

from __future__ import annotations

import json
import os
import re
import time
import random
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────

SOURCE_URL = "https://www.hioscar.com/clinical-guidelines/medical"
BASE_URL = "https://www.hioscar.com"
PDF_DIR = Path(__file__).resolve().parent.parent / "data" / "pdfs"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

PDF_URL_RE = re.compile(r'((?:https?:)?//assets\.ctfassets\.net/[^\s"\']+)', re.I)

# ── HTTP Session ─────────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
})

# ── Data Types ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PolicyLink:
    title: str
    intermediate_url: str


@dataclass
class ResolvedPolicy:
    title: str
    intermediate_url: str
    pdf_url: Optional[str]
    error: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────


def _sleep_polite(base: float = 0.5) -> None:
    time.sleep(base + random.uniform(0.0, 0.35))


def _fetch_with_retries(url: str, *, max_retries: int = 3, base_delay: float = 0.5) -> requests.Response:
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                time.sleep(base_delay * attempt)
            resp = SESSION.get(url, timeout=30)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, max_retries, url, e)
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} retries") from last_err


def _safe_filename(s: str, max_len: int = 140) -> str:
    s = re.sub(r"[^\w\s\-.()&]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return (s[:max_len] or "policy")


def _normalize_url(url: str) -> str:
    """Fix protocol-relative URLs (//assets...) to https."""
    if url.startswith("//"):
        return "https:" + url
    return url


# ── B2: Discovery ────────────────────────────────────────────────────────


def discover_intermediate_links() -> list[PolicyLink]:
    """Parse the Oscar listing page and find all PDF intermediate links.

    Strategy:
      - Find <a> elements whose visible text is exactly 'PDF'
      - Use each href as the intermediate URL
      - Derive title from nearest <li> parent text
      - Dedupe by intermediate URL
    """
    logger.info("Discovering policies from %s", SOURCE_URL)
    resp = _fetch_with_retries(SOURCE_URL, max_retries=3, base_delay=0.0)
    soup = BeautifulSoup(resp.text, "html.parser")

    results: list[PolicyLink] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True) != "PDF":
            continue

        href = a["href"].strip()
        intermediate_url = urljoin(BASE_URL, href)

        if intermediate_url in seen:
            continue
        seen.add(intermediate_url)

        # Title: parent <li> text minus trailing "PDF"
        li = a.find_parent("li")
        if li:
            title = li.get_text(" ", strip=True)
            title = re.sub(r"\s*PDF\s*$", "", title).strip()
        else:
            prev = a.find_previous(string=True)
            title = prev.strip() if prev else intermediate_url

        results.append(PolicyLink(title=title, intermediate_url=intermediate_url))

    logger.info("Discovered %d unique intermediate links", len(results))
    return results


# ── B3: PDF URL Resolution ───────────────────────────────────────────────


def extract_pdf_url(intermediate_html: str) -> Optional[str]:
    """Extract the real PDF URL from an intermediate policy page.

    Preferred: parse __NEXT_DATA__ JSON and search for ctfassets.net URLs.
    Fallback: regex scan raw HTML.
    """
    soup = BeautifulSoup(intermediate_html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")

    # 1) Next.js payload
    if script and script.string:
        try:
            data = json.loads(script.string)
            stack = [data]
            hits: list[str] = []
            while stack:
                obj = stack.pop()
                if isinstance(obj, dict):
                    stack.extend(obj.values())
                elif isinstance(obj, list):
                    stack.extend(obj)
                elif isinstance(obj, str) and "ctfassets.net" in obj:
                    hits.append(obj)

            pdf_hits = [h for h in hits if h.lower().endswith(".pdf")]
            if pdf_hits:
                return _normalize_url(pdf_hits[0])
            if hits:
                return _normalize_url(hits[0])
        except json.JSONDecodeError:
            pass

    # 2) Regex fallback
    matches = PDF_URL_RE.findall(intermediate_html)
    if not matches:
        return None

    pdf_matches = [m for m in matches if m.lower().endswith(".pdf")]
    result = pdf_matches[0] if pdf_matches else matches[0]
    return _normalize_url(result)


def resolve_policies(links: list[PolicyLink]) -> list[ResolvedPolicy]:
    """For each intermediate link, fetch the page and extract the real PDF URL."""
    resolved: list[ResolvedPolicy] = []

    for idx, link in enumerate(links, 1):
        logger.info("[%d/%d] Resolving: %s", idx, len(links), link.title)
        _sleep_polite(0.5)

        try:
            resp = _fetch_with_retries(link.intermediate_url, max_retries=3, base_delay=0.5)
            pdf_url = extract_pdf_url(resp.text)

            if not pdf_url:
                logger.warning("  No PDF URL found on %s", link.intermediate_url)
                resolved.append(ResolvedPolicy(
                    title=link.title,
                    intermediate_url=link.intermediate_url,
                    pdf_url=None,
                    error="No PDF URL found in __NEXT_DATA__ or HTML",
                ))
            else:
                logger.info("  -> PDF: %s", pdf_url[:80])
                resolved.append(ResolvedPolicy(
                    title=link.title,
                    intermediate_url=link.intermediate_url,
                    pdf_url=pdf_url,
                ))
        except Exception as e:
            logger.error("  !! Failed to resolve %s: %s", link.intermediate_url, e)
            resolved.append(ResolvedPolicy(
                title=link.title,
                intermediate_url=link.intermediate_url,
                pdf_url=None,
                error=str(e),
            ))

    return resolved


# ── B3: PDF Download ─────────────────────────────────────────────────────


def download_pdf(pdf_url: str, out_dir: Path, filename_stem: str) -> str:
    """Stream-download a PDF. Returns the saved file path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{_safe_filename(filename_stem)}.pdf"

    with SESSION.get(pdf_url, timeout=60, stream=True) as r:
        r.raise_for_status()
        ctype = r.headers.get("Content-Type", "")
        if "pdf" not in ctype.lower() and "octet-stream" not in ctype.lower():
            raise RuntimeError(f"Unexpected Content-Type {ctype} for {pdf_url}")

        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)

    if out_path.stat().st_size < 200:
        raise RuntimeError(f"Downloaded file too small ({out_path.stat().st_size}B), likely error page")

    return str(out_path)


# ── Database Integration ─────────────────────────────────────────────────


def _make_engine() -> Engine:
    db_url = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./data/app.db")
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
        pool_pre_ping=True,
    )
    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON;")
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA busy_timeout=5000;")
            cur.close()
    return engine


UPSERT_POLICY_SQL = """
INSERT INTO policies (title, pdf_url, source_page_url)
VALUES (:title, :pdf_url, :source_page_url)
ON CONFLICT(pdf_url) DO UPDATE SET
    title = excluded.title,
    source_page_url = excluded.source_page_url
"""

INSERT_DOWNLOAD_SQL = """
INSERT INTO downloads (policy_id, stored_location, http_status, error)
VALUES (:policy_id, :stored_location, :http_status, :error)
"""

GET_POLICY_ID_SQL = """
SELECT id FROM policies WHERE pdf_url = :pdf_url
"""


def run_full_pipeline() -> dict:
    """Run the complete B2+B3 pipeline: discover → resolve → download → store.

    Returns summary stats.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from backend.migrate import run_migrations
    run_migrations()

    engine = _make_engine()

    # Phase 1: Discover intermediate links
    links = discover_intermediate_links()

    # Phase 2: Resolve to real PDF URLs
    resolved = resolve_policies(links)

    # Phase 3: UPSERT policies + download PDFs
    stats = {"discovered": len(links), "resolved": 0, "downloaded": 0, "failed": 0}

    with engine.begin() as conn:
        for rp in resolved:
            # Use real PDF URL if resolved, otherwise store intermediate_url
            pdf_url = rp.pdf_url or rp.intermediate_url

            # UPSERT policy
            conn.execute(text(UPSERT_POLICY_SQL), {
                "title": rp.title,
                "pdf_url": pdf_url,
                "source_page_url": SOURCE_URL,
            })

            # Get the policy ID
            row = conn.execute(text(GET_POLICY_ID_SQL), {"pdf_url": pdf_url}).first()
            policy_id = row[0]

            if rp.pdf_url is None:
                # No PDF URL resolved — record as failed download
                conn.execute(text(INSERT_DOWNLOAD_SQL), {
                    "policy_id": policy_id,
                    "stored_location": "",
                    "http_status": None,
                    "error": rp.error or "Could not resolve PDF URL",
                })
                stats["failed"] += 1
                continue

            stats["resolved"] += 1

            # Download the PDF
            _sleep_polite(0.5)
            try:
                stored_path = download_pdf(rp.pdf_url, PDF_DIR, rp.title)
                conn.execute(text(INSERT_DOWNLOAD_SQL), {
                    "policy_id": policy_id,
                    "stored_location": stored_path,
                    "http_status": 200,
                    "error": None,
                })
                stats["downloaded"] += 1
                logger.info("  OK saved: %s", stored_path)
            except Exception as e:
                logger.error("  !! Download failed for %s: %s", rp.title, e)
                conn.execute(text(INSERT_DOWNLOAD_SQL), {
                    "policy_id": policy_id,
                    "stored_location": "",
                    "http_status": None,
                    "error": str(e),
                })
                stats["failed"] += 1

    logger.info("Pipeline complete: %s", stats)
    return stats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from dotenv import load_dotenv
    load_dotenv()

    stats = run_full_pipeline()
    print(f"\nDone! {stats}")
