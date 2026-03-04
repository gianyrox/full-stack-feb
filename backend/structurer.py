"""
B6: LLM Structuring Pipeline

Sends extracted PDF text to OpenAI GPT-4o and returns a structured JSON
criteria tree matching the oscar.json format.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI
from sqlalchemy import create_engine, event, text as sql_text

from backend.extractor import extract_text, extract_initial_section
from backend.validator import validate_structured_json

logger = logging.getLogger(__name__)

OSCAR_JSON = json.loads((Path(__file__).parent.parent / "oscar.json").read_text())

SYSTEM_PROMPT = """You are a medical policy criteria structurer. You convert medical guideline text into structured JSON decision trees.

Your output MUST be valid JSON matching this exact schema:
{
  "title": "string - descriptive title of the criteria",
  "insurance_name": "Oscar Health",
  "rules": {
    "rule_id": "string - hierarchical ID like 1, 1.1, 1.1.1",
    "rule_text": "string - the criterion text",
    "operator": "AND or OR - REQUIRED if this node has children",
    "rules": [array of child nodes with same shape - REQUIRED if operator is present]
  }
}

Rules:
- The root "rules" object is a single node (not an array)
- Leaf nodes have ONLY rule_id and rule_text (no operator, no rules array)
- Non-leaf nodes MUST have both "operator" and "rules"
- operator is "AND" when ALL criteria must be met (phrases like "all of the following", "and")
- operator is "OR" when ANY criterion suffices (phrases like "one of the following", "or")
- Use hierarchical rule_id numbering: 1, 1.1, 1.2, 1.2.1, etc.
- Extract ONLY the INITIAL authorization/approval criteria, NOT reauthorization/continuation
- Keep rule_text concise but complete

Here is an example of correct output:
""" + json.dumps(OSCAR_JSON, indent=2)

USER_PROMPT_TEMPLATE = """Extract the INITIAL medical necessity criteria from this Oscar Health clinical guideline and structure them as a JSON decision tree.

IMPORTANT:
- Extract ONLY the initial criteria (NOT reauthorization, continuation, repair, or revision criteria)
- If there are multiple criteria sections, extract only the first/initial one
- Preserve the AND/OR logic exactly as stated in the document

Guideline text:
---
{text}
---

Return ONLY the JSON object, no markdown formatting, no explanation."""


def structure_text(text: str, title_hint: str = "") -> dict:
    """Send text to OpenAI and get structured JSON back."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    user_prompt = USER_PROMPT_TEMPLATE.format(text=text[:12000])  # Token limit safety

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=4000,
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    logger.info("LLM returned structured JSON with title: %s", result.get("title", "?"))
    return result


def _make_engine():
    db_url = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./data/app.db")
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {},
        pool_pre_ping=True,
    )
    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON;")
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA busy_timeout=5000;")
            cur.close()
    return engine


UPSERT_STRUCTURED_SQL = """
INSERT INTO structured_policies (policy_id, extracted_text, structured_json, llm_model, llm_prompt, validation_error)
VALUES (:policy_id, :extracted_text, :structured_json, :llm_model, :llm_prompt, :validation_error)
ON CONFLICT(policy_id) DO UPDATE SET
    extracted_text = excluded.extracted_text,
    structured_json = excluded.structured_json,
    structured_at = CURRENT_TIMESTAMP,
    llm_model = excluded.llm_model,
    llm_prompt = excluded.llm_prompt,
    validation_error = excluded.validation_error
"""


def run_structuring(limit: int = 10) -> dict:
    """Structure at least `limit` downloaded policies.

    Picks policies that have successful downloads but no structured_policies entry yet.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from backend.migrate import run_migrations
    run_migrations()

    engine = _make_engine()

    # Find policies with successful downloads but no structuring yet
    with engine.begin() as conn:
        rows = conn.execute(sql_text("""
            SELECT p.id, p.title, d.stored_location
            FROM policies p
            JOIN downloads d ON d.policy_id = p.id AND d.error IS NULL AND d.stored_location != ''
            LEFT JOIN structured_policies sp ON sp.policy_id = p.id
            WHERE sp.id IS NULL
            ORDER BY p.id
            LIMIT :limit
        """), {"limit": limit}).mappings().all()

    if not rows:
        logger.info("No policies to structure (all done or no downloads)")
        return {"total": 0, "success": 0, "failed": 0}

    stats = {"total": len(rows), "success": 0, "failed": 0}

    for row in rows:
        policy_id = row["id"]
        title = row["title"]
        pdf_path = row["stored_location"]

        logger.info("Structuring: %s (id=%d)", title, policy_id)

        try:
            # Extract text
            extraction = extract_text(pdf_path)
            if extraction.error:
                raise RuntimeError(f"Text extraction failed: {extraction.error}")
            initial_text = extract_initial_section(extraction.text)

            # Structure with LLM
            result = structure_text(initial_text, title_hint=title)

            # Validate
            is_valid, error = validate_structured_json(result)
            validation_error = error if not is_valid else None

            if validation_error:
                logger.warning("Validation issue for %s: %s", title, validation_error)

            # Store
            with engine.begin() as conn:
                conn.execute(sql_text(UPSERT_STRUCTURED_SQL), {
                    "policy_id": policy_id,
                    "extracted_text": initial_text[:50000],  # Truncate for storage
                    "structured_json": json.dumps(result),
                    "llm_model": "gpt-4o",
                    "llm_prompt": "v1-system+user-initial-only",
                    "validation_error": validation_error,
                })

            stats["success"] += 1
            logger.info("  OK: %s", title)

        except Exception as e:
            logger.error("  FAILED: %s — %s", title, e)
            # Store the failure
            try:
                with engine.begin() as conn:
                    conn.execute(sql_text(UPSERT_STRUCTURED_SQL), {
                        "policy_id": policy_id,
                        "extracted_text": "",
                        "structured_json": "{}",
                        "llm_model": "gpt-4o",
                        "llm_prompt": "v1-system+user-initial-only",
                        "validation_error": str(e),
                    })
            except Exception:
                pass
            stats["failed"] += 1

    logger.info("Structuring complete: %s", stats)
    return stats


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    stats = run_structuring(limit=limit)
    print(f"\nDone! {stats}")
