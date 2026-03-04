# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Oscar Medical Guidelines scraper + structured criteria tree explorer. The system:
1. Discovers and downloads all medical guideline PDFs from https://www.hioscar.com/clinical-guidelines/medical
2. Uses an LLM (OpenAI) to structure at least 10 guidelines' **initial** medical necessity criteria into JSON decision trees
3. Persists scraped policy metadata and structured trees in a database
4. Provides a UI to browse policies and navigate/render criteria trees

## Key Reference Files

- `oscar.json` — Example structured output format. Recursive tree: top-level has `title`, `insurance_name`, `rules`. Each node has `rule_id`, `rule_text`, optional `operator` (AND/OR), optional `rules` array of children.
- `.env.example` — Requires `OPENAI_API_KEY`
- `README.md` — Full specification with data model requirements, acceptance criteria, and deliverables

## Data Model (Required Tables/Collections)

Three entities must be stored:
1. **Policies** — all discovered PDFs (title, pdf_url unique, source_page_url, discovered_at)
2. **Downloads** — per-policy download outcome (stored_location, http_status, error)
3. **Structured policies** — at least 10 (extracted_text, structured_json matching oscar.json schema, llm_metadata, validation_error)

## Critical Constraints

- **Initial criteria only**: When a guideline has both Initial and Continuation criteria, extract only the Initial tree. Document the selection logic.
- **Idempotent reruns**: Discovery and download must not duplicate records on re-run (pdf_url uniqueness).
- **Polite scraping**: Include throttling/rate-limiting and retries.
- **Schema validation**: LLM output must be validated against the oscar.json recursive node shape before storing.

## UI Requirements

- Policy list with title + PDF link, indicating which have structured trees
- Detail view: policy title, links, expandable/collapsible criteria tree
- AND/OR operator nodes must be visually distinct from leaf criteria nodes
