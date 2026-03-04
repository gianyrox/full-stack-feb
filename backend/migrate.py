from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./data/app.db")

def run_migrations() -> None:
    engine = create_engine(
        DB_URL,
        connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
        pool_pre_ping=True,
    )
    schema_path = Path(__file__).parent / "sql" / "sqlite_schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            conn.execute(text(stmt))

if __name__ == "__main__":
    run_migrations()
