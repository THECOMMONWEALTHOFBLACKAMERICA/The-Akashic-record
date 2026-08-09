"""Release-candidate schema baseline.

Existing pre-Alembic installations should back up first, then run
`alembic stamp 0001_release_candidate_baseline` after verifying the current schema.
Fresh installations should run `alembic upgrade head`.
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


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # Intentionally non-destructive: a baseline downgrade must not erase user knowledge.
    pass
