"""Release-candidate schema baseline.

Existing pre-Alembic installations should back up first, then run
`alembic stamp 0001_release_candidate_baseline` after verifying the current schema.
Fresh installations should run `alembic upgrade head`.

The baseline explicitly creates only the tables owned by this revision. Alembic
model discovery includes tables introduced by later revisions, so calling
`Base.metadata.create_all()` without a table list would incorrectly create those
future tables before revisions 0002-0004 run.
"""
from alembic import op

from backend.app.memory import Base
from backend.app import artifacts as _artifacts  # noqa: F401
from backend.app import control as _control  # noqa: F401
from backend.app import ingestion as _ingestion  # noqa: F401
from backend.app import jobs as _jobs  # noqa: F401

revision = "0001_release_candidate_baseline"
down_revision = None
branch_labels = None
depends_on = None

BASELINE_TABLES = (
    "memory_records",
    "documents",
    "document_chunks",
    "ingest_jobs",
    "artifacts",
    "workspaces",
    "api_keys",
    "audit_events",
    "nodes",
    "task_jobs",
)


def upgrade() -> None:
    tables = [Base.metadata.tables[name] for name in BASELINE_TABLES]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade() -> None:
    # Intentionally non-destructive: a baseline downgrade must not erase user knowledge.
    pass
