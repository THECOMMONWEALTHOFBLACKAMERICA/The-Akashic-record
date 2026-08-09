"""Add artifact IPFS publication provenance.

Revision ID: 0002_artifact_publications
Revises: 0001_release_candidate_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_artifact_publications"
down_revision = "0001_release_candidate_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact_publications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("publication_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("artifact_id", sa.String(length=64), nullable=False),
        sa.Column("artifact_cid", sa.String(length=200), nullable=False),
        sa.Column("manifest_cid", sa.String(length=200), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("publication_id"),
    )
    op.create_index("ix_artifact_publications_publication_id", "artifact_publications", ["publication_id"], unique=True)
    op.create_index("ix_artifact_publications_workspace_id", "artifact_publications", ["workspace_id"])
    op.create_index("ix_artifact_publications_artifact_id", "artifact_publications", ["artifact_id"])
    op.create_index("ix_artifact_publications_artifact_cid", "artifact_publications", ["artifact_cid"])
    op.create_index("ix_artifact_publications_manifest_cid", "artifact_publications", ["manifest_cid"])
    op.create_index("ix_artifact_publications_sha256", "artifact_publications", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_artifact_publications_sha256", table_name="artifact_publications")
    op.drop_index("ix_artifact_publications_manifest_cid", table_name="artifact_publications")
    op.drop_index("ix_artifact_publications_artifact_cid", table_name="artifact_publications")
    op.drop_index("ix_artifact_publications_artifact_id", table_name="artifact_publications")
    op.drop_index("ix_artifact_publications_workspace_id", table_name="artifact_publications")
    op.drop_index("ix_artifact_publications_publication_id", table_name="artifact_publications")
    op.drop_table("artifact_publications")
