from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .bootstrap import schema_bootstrap_enabled
from .memory import Base, engine


class TaskJob(Base):
    __tablename__ = "task_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default")
    kind: Mapped[str] = mapped_column(String(100), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(30), index=True, default="queued")
    result_json: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    assigned_node: Mapped[str] = mapped_column(String(64), default="", index=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


if schema_bootstrap_enabled():
    Base.metadata.create_all(engine)


def enqueue(kind: str, prompt: str, options: dict | None = None, workspace_id: str = "default") -> dict:
    job_id = uuid.uuid4().hex
    with Session(engine) as session:
        session.add(TaskJob(id=job_id, workspace_id=workspace_id, kind=kind, prompt=prompt, options_json=json.dumps(options or {}, ensure_ascii=False)))
        session.commit()
    return {"job_id": job_id, "status": "queued", "kind": kind}


def get_job(job_id: str) -> dict | None:
    with Session(engine) as session:
        row = session.get(TaskJob, job_id)
        return _serialize(row) if row else None


def _expired(row: TaskJob, now: datetime) -> bool:
    if row.status != "running":
        return False
    if row.lease_until is None:
        return True
    lease = row.lease_until
    if lease.tzinfo is None:
        lease = lease.replace(tzinfo=timezone.utc)
    return lease < now


def claim(node_id: str, capabilities: list[str] | None = None, lease_seconds: int = 120) -> dict | None:
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        stmt = select(TaskJob).where(TaskJob.status.in_(["queued", "running"])).order_by(TaskJob.created_at.asc()).limit(100).with_for_update(skip_locked=True)
        rows = session.scalars(stmt).all()
        candidate = next((row for row in rows if (not capabilities or row.kind in capabilities or "*" in capabilities) and (row.status == "queued" or _expired(row, now))), None)
        if not candidate:
            session.rollback()
            return None
        candidate.status = "running"
        candidate.assigned_node = node_id
        candidate.lease_until = now + timedelta(seconds=max(30, min(lease_seconds, 900)))
        candidate.attempts += 1
        candidate.updated_at = now
        session.commit()
        return _serialize(candidate, include_prompt=True)


def complete(job_id: str, node_id: str, result: dict) -> dict:
    with Session(engine) as session:
        row = session.get(TaskJob, job_id)
        if not row:
            raise KeyError(job_id)
        if row.assigned_node and row.assigned_node != node_id:
            raise PermissionError("job assigned to another node")
        row.status = "completed"
        row.result_json = json.dumps(result, ensure_ascii=False)
        row.error = ""
        row.lease_until = None
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        return _serialize(row)


def fail(job_id: str, node_id: str, error: str, retry: bool = True, max_attempts: int = 3) -> dict:
    with Session(engine) as session:
        row = session.get(TaskJob, job_id)
        if not row:
            raise KeyError(job_id)
        if row.assigned_node and row.assigned_node != node_id:
            raise PermissionError("job assigned to another node")
        row.error = error[-20_000:]
        row.status = "queued" if retry and row.attempts < max_attempts else "failed"
        row.assigned_node = ""
        row.lease_until = None
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        return _serialize(row)


def _serialize(row: TaskJob, include_prompt: bool = False) -> dict:
    out = {"job_id": row.id, "workspace_id": row.workspace_id, "kind": row.kind, "status": row.status, "result": json.loads(row.result_json) if row.result_json else None, "error": row.error, "assigned_node": row.assigned_node, "attempts": row.attempts, "created_at": row.created_at.isoformat() if row.created_at else None, "updated_at": row.updated_at.isoformat() if row.updated_at else None}
    if include_prompt:
        out["prompt"] = row.prompt
        out["options"] = json.loads(row.options_json or "{}")
    return out
