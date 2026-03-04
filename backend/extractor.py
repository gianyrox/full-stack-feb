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
            page_text = page.get_text("text", sort=True)

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


@dataclass
class SectionResult:
    text: str
    confidence: float
    logic: str


# Patterns indicating the start of the initial medical necessity criteria
_START_PATTERNS = [
    re.compile(r"(?i)initial\s+(criteria|authorization|approval)"),
    re.compile(r"(?i)criteria\s+for\s+medically\s+necessary"),
    re.compile(r"(?i)medical\s+necessity\s+criteria"),
    re.compile(r"(?i)conditions\s+for\s+coverage"),
    re.compile(r"(?i)clinical\s+indications"),
]

# Patterns indicating the start of a non-initial section (stopping points)
_END_PATTERNS = [
    re.compile(r"(?i)continuation\s+(criteria|therapy|treatment|of\s+therapy)"),
    re.compile(r"(?i)re-?authorization\s+criteria"),
    re.compile(r"(?i)renewal\s+criteria"),
    re.compile(r"(?i)repair[/,]\s*revision"),
    re.compile(r"(?i)conversion\s+criteria"),
    re.compile(r"(?i)removal\s+criteria"),
    re.compile(r"(?i)experimental\s*[/&]\s*investigational"),
    re.compile(r"(?i)relative\s+contraindications"),
    re.compile(r"(?i)applicable\s+billing\s+codes"),
    re.compile(r"(?i)HCPCS\s+(&|and)\s+CPT\s+codes"),
    re.compile(r"(?i)procedures?\s*(&|and)\s*length\s+of\s+stay"),
    re.compile(r"(?i)Medical Necessity Criteria for Reauthorization"),
]


def extract_initial_section(full_text: str) -> SectionResult:
    """Extract only the 'Initial' criteria section from full PDF text.

    Uses a line-by-line state machine approach with confidence scoring.
    Returns SectionResult with text, confidence (0.0-1.0), and extraction logic.
    """
    lines = full_text.split("\n")
    start_idx = -1
    end_idx = -1
    confidence = 0.0
    logic = "No boundaries detected."
    in_criteria = False

    for i, line in enumerate(lines):
        clean = line.strip()
        if not clean:
            continue

        if not in_criteria:
            for pattern in _START_PATTERNS:
                if pattern.search(clean):
                    start_idx = i
                    in_criteria = True
                    if "initial" in clean.lower():
                        confidence = 0.95
                        logic = f"Found explicit 'Initial' start at line {i}."
                    else:
                        confidence = 0.85
                        logic = f"Found generic criteria start at line {i}."
                    break
        else:
            for pattern in _END_PATTERNS:
                if pattern.search(clean):
                    end_idx = i
                    logic += f" End marker '{clean[:40]}...' at line {i}."
                    break

            # Heuristic: uppercase block as section break
            if end_idx == -1 and clean.isupper() and len(clean) > 10:
                if any(kw in clean for kw in ("BACKGROUND", "SUMMARY", "REFERENCES")):
                    end_idx = i
                    logic += f" Uppercase block end at line {i}."

            if end_idx != -1:
                break

    if start_idx == -1:
        return SectionResult(
            text=full_text,
            confidence=0.30,
            logic="Fallback: No start boundary found. Returning full text.",
        )

    if end_idx == -1:
        end_idx = len(lines)
        confidence -= 0.15
        logic += " Reached EOF without explicit end marker."

    section = "\n".join(lines[start_idx:end_idx])
    logger.info(
        "Extracted initial section: %d chars (confidence=%.2f)", len(section), confidence
    )
    return SectionResult(text=section, confidence=confidence, logic=logic)


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
        section = extract_initial_section(result.text)
        print(f"\nInitial section: {len(section.text)} chars (confidence={section.confidence:.2f})")
        print(f"Logic: {section.logic}")
        print(section.text[:500])
