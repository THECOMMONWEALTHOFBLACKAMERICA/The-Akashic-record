from __future__ import annotations

import os


def schema_bootstrap_enabled() -> bool:
    """Return whether model imports may create/repair tables automatically.

    Production and Alembic migration contexts disable this. Local SQLite
    development keeps legacy convenience unless TAR_AUTO_SCHEMA_BOOTSTRAP=false.
    """
    if os.getenv("TAR_MIGRATION_CONTEXT", "").lower() in {"1", "true", "yes"}:
        return False
    raw = os.getenv("TAR_AUTO_SCHEMA_BOOTSTRAP", "auto").lower().strip()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    database_url = os.getenv("TAR_DATABASE_URL", "sqlite:///./tar.db")
    return database_url.startswith("sqlite")
