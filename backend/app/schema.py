from __future__ import annotations

import os

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_workspace_columns(engine: Engine) -> None:
    """Repair pre-v0.11 local databases only outside migration discovery."""
    if os.getenv("TAR_MIGRATION_CONTEXT", "").lower() in {"1", "true", "yes"}:
        return
    targets = {
        "memory_records": "workspace_id VARCHAR(64) NOT NULL DEFAULT 'default'",
        "documents": "workspace_id VARCHAR(64) NOT NULL DEFAULT 'default'",
        "document_chunks": "workspace_id VARCHAR(64) NOT NULL DEFAULT 'default'",
        "ingest_jobs": "workspace_id VARCHAR(64) NOT NULL DEFAULT 'default'",
        "artifacts": "workspace_id VARCHAR(64) NOT NULL DEFAULT 'default'",
    }
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table_name, definition in targets.items():
            if table_name not in tables:
                continue
            columns = {c["name"] for c in inspect(engine).get_columns(table_name)}
            if "workspace_id" not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN workspace_id {definition}"))
