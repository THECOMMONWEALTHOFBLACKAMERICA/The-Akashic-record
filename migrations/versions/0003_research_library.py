"""Add workspace research library state.

Revision ID: 0003_research_library
Revises: 0002_artifact_publications
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_research_library"
down_revision = "0002_artifact_publications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "library_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("locator_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "document_id", name="uq_library_workspace_document"),
    )
    op.create_index("ix_library_entries_workspace_id", "library_entries", ["workspace_id"])
    op.create_index("ix_library_entries_document_id", "library_entries", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_library_entries_document_id", table_name="library_entries")
    op.drop_index("ix_library_entries_workspace_id", table_name="library_entries")
    op.drop_table("library_entries")
