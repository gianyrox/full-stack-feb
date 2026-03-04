from __future__ import annotations

import json
import os
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./data/app.db")

def make_engine() -> Engine:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
        pool_pre_ping=True,
    )
    if DATABASE_URL.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _conn_record) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON;")
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA busy_timeout=5000;")
            cur.close()
    return engine

engine = make_engine()

def get_conn():
    with engine.begin() as conn:
        yield conn

class PolicyListItem(BaseModel):
    id: int
    title: str
    pdf_url: str
    source_page_url: str
    discovered_at: str
    download_status: str
    has_structured_tree: bool

class DownloadAttempt(BaseModel):
    id: int
    stored_location: str
    downloaded_at: str
    http_status: Optional[int] = None
    error: Optional[str] = None

class StructuredPolicyResponse(BaseModel):
    id: int
    policy_id: int
    extracted_text: str
    structured_json: Any
    structured_at: str
    llm_model: str
    llm_prompt: str
    validation_error: Optional[str] = None

class PolicyDetail(BaseModel):
    id: int
    title: str
    pdf_url: str
    source_page_url: str
    discovered_at: str
    download_status: str
    latest_download: Optional[DownloadAttempt] = None
    structured: Optional[StructuredPolicyResponse] = None

class StatsResponse(BaseModel):
    total_policies: int
    total_downloaded: int
    total_failed: int
    total_structured: int

from backend.admin import router as admin_router

app = FastAPI(title="Medical Policy Explorer API", version="1.0.0")
app.include_router(admin_router)

allow_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allow_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LIST_SQL = """
WITH latest_download AS (
  SELECT
    d.*,
    ROW_NUMBER() OVER (PARTITION BY d.policy_id ORDER BY d.downloaded_at DESC, d.id DESC) AS rn
  FROM downloads d
)
SELECT
  p.id,
  p.title,
  p.pdf_url,
  p.source_page_url,
  p.discovered_at,
  CASE
    WHEN ld.id IS NULL THEN 'pending'
    WHEN ld.http_status BETWEEN 200 AND 299 AND (ld.error IS NULL OR ld.error = '') THEN 'success'
    ELSE 'failed'
  END AS download_status,
  CASE WHEN sp.id IS NOT NULL THEN 1 ELSE 0 END AS has_structured_tree
FROM policies p
LEFT JOIN latest_download ld
  ON ld.policy_id = p.id AND ld.rn = 1
LEFT JOIN structured_policies sp
  ON sp.policy_id = p.id
ORDER BY p.discovered_at DESC, p.id DESC;
"""

DETAIL_SQL = """
WITH latest_download AS (
  SELECT
    d.*,
    ROW_NUMBER() OVER (PARTITION BY d.policy_id ORDER BY d.downloaded_at DESC, d.id DESC) AS rn
  FROM downloads d
),
target_policy AS (
  SELECT * FROM policies WHERE id = :policy_id
)
SELECT
  p.id AS policy_id,
  p.title,
  p.pdf_url,
  p.source_page_url,
  p.discovered_at,
  ld.id AS download_id,
  ld.stored_location,
  ld.downloaded_at,
  ld.http_status,
  ld.error,
  sp.id AS structured_id,
  sp.extracted_text,
  sp.structured_json,
  sp.structured_at,
  sp.llm_model,
  sp.llm_prompt,
  sp.validation_error
FROM target_policy p
LEFT JOIN latest_download ld
  ON ld.policy_id = p.id AND ld.rn = 1
LEFT JOIN structured_policies sp
  ON sp.policy_id = p.id;
"""

TREE_SQL = """
SELECT structured_json
FROM structured_policies
WHERE policy_id = :policy_id;
"""

STATS_SQL = """
WITH latest_download AS (
  SELECT
    d.*,
    ROW_NUMBER() OVER (PARTITION BY d.policy_id ORDER BY d.downloaded_at DESC, d.id DESC) AS rn
  FROM downloads d
),
policy_status AS (
  SELECT
    p.id AS policy_id,
    ld.id AS download_id,
    CASE
      WHEN ld.id IS NULL THEN 'pending'
      WHEN ld.http_status BETWEEN 200 AND 299 AND (ld.error IS NULL OR ld.error = '') THEN 'success'
      ELSE 'failed'
    END AS download_status,
    CASE WHEN sp.id IS NOT NULL THEN 1 ELSE 0 END AS has_structured
  FROM policies p
  LEFT JOIN latest_download ld ON ld.policy_id = p.id AND ld.rn = 1
  LEFT JOIN structured_policies sp ON sp.policy_id = p.id
)
SELECT
  (SELECT COUNT(*) FROM policies) AS total_policies,
  SUM(CASE WHEN download_status = 'success' THEN 1 ELSE 0 END) AS total_downloaded,
  SUM(CASE WHEN download_status = 'failed' THEN 1 ELSE 0 END) AS total_failed,
  SUM(CASE WHEN has_structured = 1 THEN 1 ELSE 0 END) AS total_structured
FROM policy_status;
"""

def _parse_json_maybe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (str, bytes)):
        s = value.decode("utf-8") if isinstance(value, bytes) else value
        return json.loads(s)
    return value

@app.get("/api/policies", response_model=list[PolicyListItem])
def list_policies(conn: Connection = Depends(get_conn)) -> list[PolicyListItem]:
    rows = conn.execute(text(LIST_SQL)).mappings().all()
    return [
        PolicyListItem(
            id=row["id"],
            title=row["title"],
            pdf_url=row["pdf_url"],
            source_page_url=row["source_page_url"],
            discovered_at=str(row["discovered_at"]),
            download_status=row["download_status"],
            has_structured_tree=bool(row["has_structured_tree"]),
        )
        for row in rows
    ]

@app.get("/api/policies/{policy_id}", response_model=PolicyDetail)
def get_policy_detail(policy_id: int, conn: Connection = Depends(get_conn)) -> PolicyDetail:
    row = conn.execute(text(DETAIL_SQL), {"policy_id": policy_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Policy not found")

    if row["download_id"] is None:
        download_status = "pending"
    elif (row["http_status"] is not None and 200 <= int(row["http_status"]) <= 299) and (row["error"] in (None, "")):
        download_status = "success"
    else:
        download_status = "failed"

    latest_download = None
    if row["download_id"] is not None:
        latest_download = DownloadAttempt(
            id=int(row["download_id"]),
            stored_location=row["stored_location"],
            downloaded_at=str(row["downloaded_at"]),
            http_status=row["http_status"],
            error=row["error"],
        )

    structured = None
    if row["structured_id"] is not None:
        structured = StructuredPolicyResponse(
            id=int(row["structured_id"]),
            policy_id=policy_id,
            extracted_text=row["extracted_text"],
            structured_json=_parse_json_maybe(row["structured_json"]),
            structured_at=str(row["structured_at"]),
            llm_model=row["llm_model"],
            llm_prompt=row["llm_prompt"],
            validation_error=row["validation_error"],
        )

    return PolicyDetail(
        id=policy_id,
        title=row["title"],
        pdf_url=row["pdf_url"],
        source_page_url=row["source_page_url"],
        discovered_at=str(row["discovered_at"]),
        download_status=download_status,
        latest_download=latest_download,
        structured=structured,
    )

@app.get("/api/policies/{policy_id}/tree")
def get_policy_tree(policy_id: int, conn: Connection = Depends(get_conn)) -> Any:
    row = conn.execute(text(TREE_SQL), {"policy_id": policy_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Structured tree not found for this policy")
    try:
        return _parse_json_maybe(row["structured_json"])
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Stored structured_json is not valid JSON")

@app.get("/api/stats", response_model=StatsResponse)
def get_stats(conn: Connection = Depends(get_conn)) -> StatsResponse:
    row = conn.execute(text(STATS_SQL)).mappings().first()
    if not row:
        return StatsResponse(total_policies=0, total_downloaded=0, total_failed=0, total_structured=0)
    return StatsResponse(
        total_policies=int(row["total_policies"] or 0),
        total_downloaded=int(row["total_downloaded"] or 0),
        total_failed=int(row["total_failed"] or 0),
        total_structured=int(row["total_structured"] or 0),
    )

@app.on_event("startup")
def on_startup():
    from backend.migrate import run_migrations
    run_migrations()
