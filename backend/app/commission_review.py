from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .commission import CommissionEvidence, EVIDENCE_STATUSES, SOURCE_TIERS, serialize_evidence
from .control import audit
from .memory import engine


def review_and_retier_evidence(
    evidence_id: str,
    workspace_id: str,
    *,
    status: str,
    reviewer: str,
    source_tier: int | None = None,
    review_notes: str = "",
    exclusion_reason: str = "",
) -> dict:
    if status not in EVIDENCE_STATUSES:
        raise ValueError("invalid evidence status")
    if source_tier is not None and source_tier not in SOURCE_TIERS:
        raise ValueError("source_tier must be 1, 2, or 3")
    if status == "excluded" and not exclusion_reason.strip():
        raise ValueError("excluded evidence requires an exclusion reason")

    with Session(engine) as session:
        row = session.scalar(
            select(CommissionEvidence).where(
                CommissionEvidence.evidence_id == evidence_id,
                CommissionEvidence.workspace_id == workspace_id,
            )
        )
        if not row:
            raise KeyError("evidence not found")
        old_tier = row.source_tier
        if source_tier is not None:
            row.source_tier = source_tier
        row.status = status
        row.reviewer = reviewer
        row.review_notes = review_notes[:20000]
        row.exclusion_reason = exclusion_reason[:20000]
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(row)

    audit(
        "commission.evidence_reviewed",
        "commission_evidence",
        evidence_id,
        {
            "status": status,
            "case_id": row.case_id,
            "source_tier_before": old_tier,
            "source_tier_after": row.source_tier,
        },
        workspace_id=workspace_id,
        actor=reviewer,
    )
    return serialize_evidence(row)
