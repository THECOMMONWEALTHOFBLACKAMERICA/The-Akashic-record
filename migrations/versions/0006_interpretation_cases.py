"""Add T.A.R. Human Interpretation Protocol cases.

Revision ID: 0006_interpretation_cases
Revises: 0005_commission_cases
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_interpretation_cases"
down_revision = "0005_commission_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interpretation_cases",
        sa.Column("case_id", sa.String(length=64), primary_key=True),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("subject_ref", sa.String(length=200), nullable=False, server_default="anonymous"),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("evaluation_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interpretation_cases_workspace_id", "interpretation_cases", ["workspace_id"])
    op.create_index("ix_interpretation_cases_subject_ref", "interpretation_cases", ["subject_ref"])


def downgrade() -> None:
    op.drop_index("ix_interpretation_cases_subject_ref", table_name="interpretation_cases")
    op.drop_index("ix_interpretation_cases_workspace_id", table_name="interpretation_cases")
    op.drop_table("interpretation_cases")
