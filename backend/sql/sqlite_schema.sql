PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS policies (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  title           TEXT NOT NULL,
  pdf_url         TEXT NOT NULL UNIQUE,
  source_page_url TEXT NOT NULL,
  discovered_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS downloads (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  policy_id      INTEGER NOT NULL,
  stored_location TEXT NOT NULL,
  downloaded_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  http_status    INTEGER,
  error          TEXT NULL,
  FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS structured_policies (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  policy_id        INTEGER NOT NULL UNIQUE,
  extracted_text   TEXT NOT NULL,
  structured_json  TEXT NOT NULL,
  structured_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  llm_model        TEXT NOT NULL,
  llm_prompt       TEXT NOT NULL,
  validation_error TEXT NULL,
  FOREIGN KEY (policy_id) REFERENCES policies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_policies_discovered_at
  ON policies(discovered_at DESC);

CREATE INDEX IF NOT EXISTS idx_policies_title
  ON policies(title);

CREATE INDEX IF NOT EXISTS idx_downloads_policy_downloaded_at
  ON downloads(policy_id, downloaded_at DESC);
