"""
B5: PDF Text Extractor

Extracts text from downloaded PDFs using PyMuPDF (fitz).
Preserves page structure and numbering for LLM consumption.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    text: str
    page_count: int
    error: Optional[str] = None


def extract_text(pdf_path: str | Path) -> ExtractionResult:
    """Extract text from a PDF file.

    Returns full text with page markers, preserving numbered lists and hierarchy.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return ExtractionResult(text="", page_count=0, error=f"File not found: {pdf_path}")

    try:
        doc = fitz.open(str(pdf_path))
        pages: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text("text")

            # Strip common headers/footers (page numbers, copyright lines)
            lines = page_text.split("\n")
            filtered = _strip_headers_footers(lines, page_num + 1, len(doc))
            pages.append("\n".join(filtered))

        doc.close()

        full_text = "\n\n".join(
            f"--- Page {i+1} ---\n{p}" for i, p in enumerate(pages) if p.strip()
        )

        return ExtractionResult(text=full_text, page_count=len(pages))

    except Exception as e:
        logger.error("Failed to extract text from %s: %s", pdf_path, e)
        return ExtractionResult(text="", page_count=0, error=str(e))


def _strip_headers_footers(lines: list[str], page_num: int, total_pages: int) -> list[str]:
    """Remove common header/footer patterns from extracted lines."""
    filtered = []
    for line in lines:
        stripped = line.strip()

        # Skip empty lines at start/end (will be re-added by join)
        if not stripped:
            filtered.append("")
            continue

        # Skip standalone page numbers
        if re.match(r"^\d+$", stripped):
            continue
        if re.match(r"^Page\s+\d+\s*(of\s+\d+)?$", stripped, re.I):
            continue

        # Skip "Confidential" / copyright footers
        if re.match(r"^(confidential|©|\u00a9|all rights reserved)", stripped, re.I):
            continue

        filtered.append(line)

    return filtered


def extract_initial_section(full_text: str) -> str:
    """Extract only the 'Initial' criteria section from full PDF text.

    Looks for common heading patterns and slices text to just that section.
    Returns full text as fallback if no clear initial section found.
    """
    # Patterns that mark the START of initial criteria
    initial_patterns = [
        r"Medical Necessity Criteria for Initial Authorization",
        r"Initial Authorization Criteria",
        r"Initial Approval Criteria",
        r"Initial Criteria",
        r"Clinical Indications",
    ]

    # Patterns that mark the END (start of non-initial sections)
    end_patterns = [
        r"Medical Necessity Criteria for Reauthorization",
        r"Reauthorization Criteria",
        r"Continued?\s*Care",
        r"Continuation of Services",
        r"Renewal Criteria",
        r"Re-?authorization",
    ]

    # Find the initial section start
    initial_start = None
    for pattern in initial_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            initial_start = match.start()
            break

    if initial_start is None:
        # No explicit initial section — return full text for LLM to handle
        logger.info("No explicit initial section found, returning full text")
        return full_text

    # Find the end of the initial section
    text_after_start = full_text[initial_start:]
    initial_end = len(full_text)

    for pattern in end_patterns:
        match = re.search(pattern, text_after_start[100:], re.IGNORECASE)  # skip the heading itself
        if match:
            candidate_end = initial_start + 100 + match.start()
            if candidate_end < initial_end:
                initial_end = candidate_end

    section = full_text[initial_start:initial_end].strip()
    logger.info("Extracted initial section: %d chars (from %d total)", len(section), len(full_text))
    return section


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python -m backend.extractor <pdf_path>")
        sys.exit(1)

    result = extract_text(sys.argv[1])
    print(f"Pages: {result.page_count}")
    print(f"Text length: {len(result.text)} chars")
    if result.error:
        print(f"Error: {result.error}")
    else:
        # Show first 500 chars
        print(result.text[:500])
        print("---")
        # Try initial section extraction
        initial = extract_initial_section(result.text)
        print(f"\nInitial section: {len(initial)} chars")
        print(initial[:500])
