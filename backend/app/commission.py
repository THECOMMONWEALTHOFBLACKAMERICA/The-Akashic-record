from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .bootstrap import schema_bootstrap_enabled
from .control import audit
from .memory import Base, engine

EVIDENCE_STATUSES = {"verified", "corroborated", "conflicting", "unverified", "insufficient", "excluded"}
SOURCE_TIERS = {1, 2, 3}
CASE_STATUSES = {"open", "under_review", "approved", "denied", "withdrawn", "incomplete", "appealed", "closed"}


class CommissionCase(Base):
    __tablename__ = "commission_cases"
    case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True)
    application_ref: Mapped[str] = mapped_column(String(200), index=True, default="")
    applicant_label: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(40), index=True, default="open")
    restricted_research: Mapped[bool] = mapped_column(Boolean, default=True)
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    retention_policy: Mapped[str] = mapped_column(String(200), default="pending-policy")
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CommissionEvidence(Base):
    __tablename__ = "commission_evidence"
    __table_args__ = (UniqueConstraint("case_id", "evidence_id", name="uq_commission_case_evidence"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    case_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(1000))
    source_tier: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), index=True, default="unverified")
    source: Mapped[str] = mapped_column(String(300), default="")
    source_uri: Mapped[str] = mapped_column(String(3000), default="")
    citation: Mapped[str] = mapped_column(Text, default="")
    retrieval_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    original_filename: Mapped[str] = mapped_column(String(1000), default="")
    original_sha256: Mapped[str] = mapped_column(String(64), index=True, default="")
    uploader: Mapped[str] = mapped_column(String(500), default="")
    claimed_provenance: Mapped[str] = mapped_column(Text, default="")
    media_type: Mapped[str] = mapped_column(String(200), default="application/octet-stream")
    transformations_json: Mapped[str] = mapped_column(Text, default="[]")
    derived_artifacts_json: Mapped[str] = mapped_column(Text, default="[]")
    reviewer: Mapped[str] = mapped_column(String(500), default="")
    review_notes: Mapped[str] = mapped_column(Text, default="")
    exclusion_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


if schema_bootstrap_enabled():
    Base.metadata.create_all(engine)


def _case(session: Session, case_id: str, workspace_id: str) -> CommissionCase:
    row = session.scalar(select(CommissionCase).where(CommissionCase.case_id == case_id, CommissionCase.workspace_id == workspace_id))
    if not row:
        raise KeyError("case not found")
    return row


def create_case(workspace_id: str, application_ref: str = "", applicant_label: str = "", actor: str = "system") -> dict:
    case_id = uuid.uuid4().hex
    with Session(engine) as session:
        row = CommissionCase(case_id=case_id, workspace_id=workspace_id, application_ref=application_ref, applicant_label=applicant_label)
        session.add(row); session.commit(); session.refresh(row)
    audit("commission.case_created", "commission_case", case_id, {"application_ref": application_ref}, workspace_id=workspace_id, actor=actor)
    return serialize_case(row)


def list_cases(workspace_id: str, limit: int = 200) -> list[dict]:
    with Session(engine) as session:
        rows = session.scalars(select(CommissionCase).where(CommissionCase.workspace_id == workspace_id).order_by(CommissionCase.created_at.desc()).limit(limit)).all()
        return [serialize_case(r) for r in rows]


def update_case(case_id: str, workspace_id: str, *, status: str | None = None, restricted_research: bool | None = None, legal_hold: bool | None = None, retention_policy: str | None = None, actor: str = "system") -> dict:
    if status is not None and status not in CASE_STATUSES: raise ValueError("invalid case status")
    with Session(engine) as session:
        row = _case(session, case_id, workspace_id)
        if status is not None: row.status = status
        if restricted_research is not None: row.restricted_research = restricted_research
        if legal_hold is not None: row.legal_hold = legal_hold
        if retention_policy is not None: row.retention_policy = retention_policy[:200]
        row.updated_at = datetime.now(timezone.utc)
        session.commit(); session.refresh(row)
    audit("commission.case_updated", "commission_case", case_id, {"status": status, "restricted_research": restricted_research, "legal_hold": legal_hold}, workspace_id=workspace_id, actor=actor)
    return serialize_case(row)


def add_evidence(case_id: str, workspace_id: str, *, title: str, source_tier: int, source: str = "", source_uri: str = "", citation: str = "", retrieval_metadata: dict | None = None, original_filename: str = "", original_bytes: bytes | None = None, original_sha256: str = "", uploader: str = "", claimed_provenance: str = "", media_type: str = "application/octet-stream", transformations: list | None = None, derived_artifacts: list | None = None, actor: str = "system") -> dict:
    if source_tier not in SOURCE_TIERS: raise ValueError("source_tier must be 1, 2, or 3")
    digest = hashlib.sha256(original_bytes).hexdigest() if original_bytes is not None else original_sha256
    evidence_id = uuid.uuid4().hex
    with Session(engine) as session:
        _case(session, case_id, workspace_id)
        row = CommissionEvidence(evidence_id=evidence_id, case_id=case_id, workspace_id=workspace_id, title=title, source_tier=source_tier, status="unverified", source=source, source_uri=source_uri, citation=citation, retrieval_metadata_json=json.dumps(retrieval_metadata or {}, ensure_ascii=False), original_filename=original_filename, original_sha256=digest, uploader=uploader, claimed_provenance=claimed_provenance, media_type=media_type, transformations_json=json.dumps(transformations or [], ensure_ascii=False), derived_artifacts_json=json.dumps(derived_artifacts or [], ensure_ascii=False))
        session.add(row); session.commit(); session.refresh(row)
    audit("commission.evidence_added", "commission_evidence", evidence_id, {"case_id": case_id, "tier": source_tier, "sha256": digest}, workspace_id=workspace_id, actor=actor)
    return serialize_evidence(row)


def review_evidence(evidence_id: str, workspace_id: str, *, status: str, reviewer: str, review_notes: str = "", exclusion_reason: str = "") -> dict:
    if status not in EVIDENCE_STATUSES: raise ValueError("invalid evidence status")
    if status == "excluded" and not exclusion_reason.strip(): raise ValueError("excluded evidence requires an exclusion reason")
    with Session(engine) as session:
        row = session.scalar(select(CommissionEvidence).where(CommissionEvidence.evidence_id == evidence_id, CommissionEvidence.workspace_id == workspace_id))
        if not row: raise KeyError("evidence not found")
        row.status = status; row.reviewer = reviewer; row.review_notes = review_notes[:20000]; row.exclusion_reason = exclusion_reason[:20000]; row.updated_at = datetime.now(timezone.utc)
        session.commit(); session.refresh(row)
    audit("commission.evidence_reviewed", "commission_evidence", evidence_id, {"status": status, "case_id": row.case_id}, workspace_id=workspace_id, actor=reviewer)
    return serialize_evidence(row)


def list_evidence(case_id: str, workspace_id: str) -> list[dict]:
    with Session(engine) as session:
        _case(session, case_id, workspace_id)
        rows = session.scalars(select(CommissionEvidence).where(CommissionEvidence.case_id == case_id, CommissionEvidence.workspace_id == workspace_id).order_by(CommissionEvidence.created_at.asc())).all()
        return [serialize_evidence(r) for r in rows]


def export_case(case_id: str, workspace_id: str) -> dict:
    with Session(engine) as session:
        case = _case(session, case_id, workspace_id)
        rows = session.scalars(select(CommissionEvidence).where(CommissionEvidence.case_id == case_id, CommissionEvidence.workspace_id == workspace_id).order_by(CommissionEvidence.created_at.asc())).all()
        return {"case": serialize_case(case), "evidence": [serialize_evidence(r) for r in rows], "exported_at": datetime.now(timezone.utc).isoformat()}


def delete_case(case_id: str, workspace_id: str, *, actor: str, policy_basis: str) -> dict:
    if not policy_basis.strip(): raise ValueError("policy_basis is required")
    with Session(engine) as session:
        case = _case(session, case_id, workspace_id)
        if case.legal_hold: raise PermissionError("case is under legal hold")
        evidence_rows = session.scalars(select(CommissionEvidence).where(CommissionEvidence.case_id == case_id, CommissionEvidence.workspace_id == workspace_id)).all()
        count = len(evidence_rows)
        for row in evidence_rows: session.delete(row)
        session.delete(case); session.commit()
    audit("commission.case_deleted", "commission_case", case_id, {"policy_basis": policy_basis, "evidence_records_deleted": count}, workspace_id=workspace_id, actor=actor)
    return {"deleted": True, "case_id": case_id, "evidence_records_deleted": count}


def serialize_case(row: CommissionCase) -> dict:
    return {"case_id": row.case_id, "workspace_id": row.workspace_id, "application_ref": row.application_ref, "applicant_label": row.applicant_label, "status": row.status, "restricted_research": row.restricted_research, "legal_hold": row.legal_hold, "retention_policy": row.retention_policy, "retention_until": row.retention_until.isoformat() if row.retention_until else None, "created_at": row.created_at.isoformat() if row.created_at else None, "updated_at": row.updated_at.isoformat() if row.updated_at else None}


def serialize_evidence(row: CommissionEvidence) -> dict:
    return {"evidence_id": row.evidence_id, "case_id": row.case_id, "workspace_id": row.workspace_id, "title": row.title, "source_tier": row.source_tier, "status": row.status, "source": row.source, "source_uri": row.source_uri, "citation": row.citation, "retrieval_metadata": json.loads(row.retrieval_metadata_json or "{}"), "original_filename": row.original_filename, "original_sha256": row.original_sha256, "uploader": row.uploader, "claimed_provenance": row.claimed_provenance, "media_type": row.media_type, "transformations": json.loads(row.transformations_json or "[]"), "derived_artifacts": json.loads(row.derived_artifacts_json or "[]"), "reviewer": row.reviewer, "review_notes": row.review_notes, "exclusion_reason": row.exclusion_reason, "created_at": row.created_at.isoformat() if row.created_at else None, "updated_at": row.updated_at.isoformat() if row.updated_at else None}
