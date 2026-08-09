from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .bootstrap import in_migration_context, schema_bootstrap_enabled
from .memory import Base, engine


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    owner: Mapped[str] = mapped_column(String(500), default="local")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(500))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default")
    actor: Mapped[str] = mapped_column(String(500), default="system")
    action: Mapped[str] = mapped_column(String(200), index=True)
    object_type: Mapped[str] = mapped_column(String(200), default="")
    object_id: Mapped[str] = mapped_column(String(500), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class NodeRecord(Base):
    __tablename__ = "nodes"
    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    endpoint: Mapped[str] = mapped_column(String(3000), default="")
    capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    reputation: Mapped[float] = mapped_column(Float, default=1.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


if schema_bootstrap_enabled():
    Base.metadata.create_all(engine)


def ensure_default_workspace() -> None:
    with Session(engine) as session:
        if not session.get(Workspace, "default"):
            session.add(Workspace(id="default", name="T.A.R. Default Workspace", owner="local"))
            session.commit()


if not in_migration_context():
    ensure_default_workspace()


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create_api_key(label: str, workspace_id: str = "default") -> dict:
    raw = "tar_" + secrets.token_urlsafe(32)
    with Session(engine) as session:
        if not session.get(Workspace, workspace_id):
            raise ValueError("Unknown workspace")
        row = ApiKey(label=label, key_hash=_hash_key(raw), workspace_id=workspace_id)
        session.add(row)
        session.commit()
        session.refresh(row)
        key_id = str(row.id)
    audit("api_key.created", "api_key", label, {"workspace_id": workspace_id, "key_id": key_id}, workspace_id=workspace_id)
    return {"api_key": raw, "key_id": key_id, "label": label, "workspace_id": workspace_id}


def verify_api_key(raw: str) -> dict | None:
    if not raw:
        return None
    with Session(engine) as session:
        row = session.scalar(select(ApiKey).where(ApiKey.key_hash == _hash_key(raw), ApiKey.active.is_(True)))
        return {"workspace_id": row.workspace_id, "label": row.label, "key_id": str(row.id)} if row else None


def create_workspace(name: str, owner: str = "local") -> dict:
    wid = uuid.uuid4().hex
    with Session(engine) as session:
        session.add(Workspace(id=wid, name=name, owner=owner))
        session.commit()
    audit("workspace.created", "workspace", wid, {"name": name, "owner": owner}, workspace_id=wid, actor=owner)
    return {"id": wid, "name": name, "owner": owner}


def audit(action: str, object_type: str = "", object_id: str = "", payload: dict | None = None, *, workspace_id: str = "default", actor: str = "system") -> dict:
    event_id = uuid.uuid4().hex
    created = datetime.now(timezone.utc).isoformat()
    with Session(engine) as session:
        workspace = session.scalar(select(Workspace).where(Workspace.id == workspace_id).with_for_update())
        if not workspace:
            raise ValueError(f"Unknown workspace for audit event: {workspace_id}")
        previous = session.scalar(select(AuditEvent).where(AuditEvent.workspace_id == workspace_id).order_by(AuditEvent.id.desc()).limit(1))
        prev_hash = previous.event_hash if previous else ""
        canonical = json.dumps({"event_id": event_id, "workspace_id": workspace_id, "actor": actor, "action": action, "object_type": object_type, "object_id": object_id, "payload": payload or {}, "prev_hash": prev_hash, "created_at": created}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        event_hash = hashlib.sha256(canonical.encode()).hexdigest()
        session.add(AuditEvent(event_id=event_id, workspace_id=workspace_id, actor=actor, action=action, object_type=object_type, object_id=object_id, payload_json=json.dumps({"payload": payload or {}, "canonical_created_at": created}, ensure_ascii=False), prev_hash=prev_hash, event_hash=event_hash))
        session.commit()
    return {"event_id": event_id, "event_hash": event_hash, "prev_hash": prev_hash}


def audit_tail(limit: int = 100, workspace_id: str | None = None) -> list[dict]:
    with Session(engine) as session:
        stmt = select(AuditEvent)
        if workspace_id:
            stmt = stmt.where(AuditEvent.workspace_id == workspace_id)
        rows = session.scalars(stmt.order_by(AuditEvent.id.desc()).limit(limit)).all()
    return [{"event_id": r.event_id, "workspace_id": r.workspace_id, "actor": r.actor, "action": r.action, "object_type": r.object_type, "object_id": r.object_id, "payload": json.loads(r.payload_json or "{}").get("payload", {}), "prev_hash": r.prev_hash, "event_hash": r.event_hash, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


def verify_audit_chain(workspace_id: str = "default") -> dict:
    with Session(engine) as session:
        rows = session.scalars(select(AuditEvent).where(AuditEvent.workspace_id == workspace_id).order_by(AuditEvent.id.asc())).all()
    previous = ""
    for row in rows:
        stored = json.loads(row.payload_json or "{}")
        canonical_created_at = stored.get("canonical_created_at")
        payload = stored.get("payload", {})
        if not canonical_created_at:
            return {"valid": False, "events": len(rows), "failed_event": row.event_id, "reason": "legacy event lacks canonical timestamp"}
        canonical = json.dumps({"event_id": row.event_id, "workspace_id": row.workspace_id, "actor": row.actor, "action": row.action, "object_type": row.object_type, "object_id": row.object_id, "payload": payload, "prev_hash": previous, "created_at": canonical_created_at}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        expected = hashlib.sha256(canonical.encode()).hexdigest()
        if row.prev_hash != previous or row.event_hash != expected:
            return {"valid": False, "events": len(rows), "failed_event": row.event_id, "reason": "hash mismatch"}
        previous = row.event_hash
    return {"valid": True, "events": len(rows), "head": previous, "workspace_id": workspace_id}


def register_node(name: str, endpoint: str = "", capabilities: list[str] | None = None) -> dict:
    node_id = uuid.uuid4().hex
    with Session(engine) as session:
        session.add(NodeRecord(node_id=node_id, name=name, endpoint=endpoint, capabilities_json=json.dumps(capabilities or [])))
        session.commit()
    audit("node.registered", "node", node_id, {"name": name, "endpoint": endpoint, "capabilities": capabilities or []})
    return {"node_id": node_id, "name": name, "endpoint": endpoint, "capabilities": capabilities or []}


def heartbeat_node(node_id: str) -> dict | None:
    with Session(engine) as session:
        row = session.get(NodeRecord, node_id)
        if not row:
            return None
        row.last_seen = datetime.now(timezone.utc)
        row.active = True
        session.commit()
        return {"node_id": row.node_id, "last_seen": row.last_seen.isoformat(), "reputation": row.reputation}


def list_nodes() -> list[dict]:
    with Session(engine) as session:
        rows = session.scalars(select(NodeRecord).order_by(NodeRecord.last_seen.desc())).all()
    return [{"node_id": r.node_id, "name": r.name, "endpoint": r.endpoint, "capabilities": json.loads(r.capabilities_json or "[]"), "reputation": r.reputation, "active": r.active, "last_seen": r.last_seen.isoformat() if r.last_seen else None} for r in rows]
