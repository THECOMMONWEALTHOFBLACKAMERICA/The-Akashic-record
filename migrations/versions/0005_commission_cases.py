"""Add Foundational Citizenship Commission case/evidence records.

Revision ID: 0005_commission_cases
Revises: 0004_autonomous_agent_runs
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_commission_cases"
down_revision = "0004_autonomous_agent_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commission_cases",
        sa.Column("case_id", sa.String(length=64), primary_key=True),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("application_ref", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("applicant_label", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="open"),
        sa.Column("restricted_research", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retention_policy", sa.String(length=200), nullable=False, server_default="pending-policy"),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_commission_cases_workspace_id", "commission_cases", ["workspace_id"])
    op.create_index("ix_commission_cases_application_ref", "commission_cases", ["application_ref"])
    op.create_index("ix_commission_cases_status", "commission_cases", ["status"])

    op.create_table(
        "commission_evidence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("source_tier", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="unverified"),
        sa.Column("source", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("source_uri", sa.String(length=3000), nullable=False, server_default=""),
        sa.Column("citation", sa.Text(), nullable=False, server_default=""),
        sa.Column("retrieval_metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("original_filename", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("original_sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("uploader", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("claimed_provenance", sa.Text(), nullable=False, server_default=""),
        sa.Column("media_type", sa.String(length=200), nullable=False, server_default="application/octet-stream"),
        sa.Column("transformations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("derived_artifacts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("reviewer", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("review_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("exclusion_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("evidence_id"),
        sa.UniqueConstraint("case_id", "evidence_id", name="uq_commission_case_evidence"),
    )
    op.create_index("ix_commission_evidence_evidence_id", "commission_evidence", ["evidence_id"], unique=True)
    op.create_index("ix_commission_evidence_case_id", "commission_evidence", ["case_id"])
    op.create_index("ix_commission_evidence_workspace_id", "commission_evidence", ["workspace_id"])
    op.create_index("ix_commission_evidence_status", "commission_evidence", ["status"])
    op.create_index("ix_commission_evidence_original_sha256", "commission_evidence", ["original_sha256"])


def downgrade() -> None:
    op.drop_index("ix_commission_evidence_original_sha256", table_name="commission_evidence")
    op.drop_index("ix_commission_evidence_status", table_name="commission_evidence")
    op.drop_index("ix_commission_evidence_workspace_id", table_name="commission_evidence")
    op.drop_index("ix_commission_evidence_case_id", table_name="commission_evidence")
    op.drop_index("ix_commission_evidence_evidence_id", table_name="commission_evidence")
    op.drop_table("commission_evidence")
    op.drop_index("ix_commission_cases_status", table_name="commission_cases")
    op.drop_index("ix_commission_cases_application_ref", table_name="commission_cases")
    op.drop_index("ix_commission_cases_workspace_id", table_name="commission_cases")
    op.drop_table("commission_cases")
