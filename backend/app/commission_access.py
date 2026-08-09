from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .bootstrap import schema_bootstrap_enabled
from .memory import Base, engine

ROLES = {"owner", "commissioner", "staff", "reviewer", "readonly"}


class CommissionCaseAccess(Base):
    __tablename__ = "commission_case_access"
    __table_args__ = (UniqueConstraint("case_id", "key_id", name="uq_commission_case_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True)
    key_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(40), default="readonly")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


if schema_bootstrap_enabled():
    Base.metadata.create_all(engine)


def grant_case_access(case_id: str, workspace_id: str, key_id: str, role: str = "readonly") -> dict:
    if not key_id:
        raise ValueError("authenticated key_id required")
    if role not in ROLES:
        raise ValueError("invalid Commission case role")
    with Session(engine) as session:
        row = session.scalar(select(CommissionCaseAccess).where(CommissionCaseAccess.case_id == case_id, CommissionCaseAccess.key_id == key_id))
        if row is None:
            row = CommissionCaseAccess(case_id=case_id, workspace_id=workspace_id, key_id=key_id, role=role)
            session.add(row)
        else:
            if row.workspace_id != workspace_id:
                raise PermissionError("case access workspace mismatch")
            row.role = role
        session.commit(); session.refresh(row)
        return serialize_access(row)


def has_case_access(case_id: str, workspace_id: str, key_id: str, *, write: bool = False, review: bool = False) -> bool:
    if not key_id:
        return False
    with Session(engine) as session:
        row = session.scalar(select(CommissionCaseAccess).where(CommissionCaseAccess.case_id == case_id, CommissionCaseAccess.workspace_id == workspace_id, CommissionCaseAccess.key_id == key_id))
        if not row:
            return False
        if review:
            return row.role in {"owner", "commissioner", "reviewer"}
        if write:
            return row.role in {"owner", "commissioner", "staff", "reviewer"}
        return row.role in ROLES


def accessible_case_ids(workspace_id: str, key_id: str) -> set[str]:
    if not key_id:
        return set()
    with Session(engine) as session:
        rows = session.scalars(select(CommissionCaseAccess).where(CommissionCaseAccess.workspace_id == workspace_id, CommissionCaseAccess.key_id == key_id)).all()
        return {r.case_id for r in rows}


def list_case_access(case_id: str, workspace_id: str) -> list[dict]:
    with Session(engine) as session:
        rows = session.scalars(select(CommissionCaseAccess).where(CommissionCaseAccess.case_id == case_id, CommissionCaseAccess.workspace_id == workspace_id)).all()
        return [serialize_access(r) for r in rows]


def revoke_case_access(case_id: str, workspace_id: str, key_id: str) -> bool:
    with Session(engine) as session:
        row = session.scalar(select(CommissionCaseAccess).where(CommissionCaseAccess.case_id == case_id, CommissionCaseAccess.workspace_id == workspace_id, CommissionCaseAccess.key_id == key_id))
        if not row:
            return False
        session.delete(row); session.commit(); return True


def serialize_access(row: CommissionCaseAccess) -> dict:
    return {"case_id": row.case_id, "workspace_id": row.workspace_id, "key_id": row.key_id, "role": row.role, "created_at": row.created_at.isoformat() if row.created_at else None}
