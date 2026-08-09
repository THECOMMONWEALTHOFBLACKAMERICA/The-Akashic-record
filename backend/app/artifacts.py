from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .bootstrap import schema_bootstrap_enabled
from .memory import Base, engine
from .schema import ensure_workspace_columns
from .storage import configured_storage, delete_artifact_uri, read_artifact_uri


class ArtifactRecord(Base):
    __tablename__ = "artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default")
    name: Mapped[str] = mapped_column(String(1000))
    media_type: Mapped[str] = mapped_column(String(200), default="application/octet-stream")
    path: Mapped[str] = mapped_column(String(3000))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


if schema_bootstrap_enabled():
    Base.metadata.create_all(engine)
    ensure_workspace_columns(engine)


def _safe_name(name: str, fallback: str) -> str:
    return "".join(c for c in Path(name).name if c.isalnum() or c in "._-") or fallback


def artifact_metadata(row: ArtifactRecord) -> dict:
    return json.loads(row.metadata_json or "{}")


def is_protected_artifact(row: ArtifactRecord) -> bool:
    metadata = artifact_metadata(row)
    return metadata.get("classification") == "commission_original_evidence" or metadata.get("public_ipfs_allowed") is False


def save_artifact(name: str, data: bytes, media_type: str, metadata: dict | None = None, workspace_id: str = "default") -> dict:
    artifact_id = uuid.uuid4().hex
    safe = _safe_name(name, artifact_id)
    object_name = f"{artifact_id}-{safe}"
    digest = hashlib.sha256(data).hexdigest()
    storage = configured_storage()
    uri = storage.put(workspace_id, object_name, data, media_type)
    enriched_metadata = {"storage_backend": storage.name, **(metadata or {})}
    try:
        with Session(engine) as session:
            session.add(ArtifactRecord(artifact_id=artifact_id, workspace_id=workspace_id, name=safe, media_type=media_type, path=uri, sha256=digest, size_bytes=len(data), metadata_json=json.dumps(enriched_metadata, ensure_ascii=False)))
            session.commit()
    except Exception:
        try:
            storage.delete(uri)
        finally:
            raise
    return {"artifact_id": artifact_id, "name": safe, "media_type": media_type, "sha256": digest, "size_bytes": len(data), "workspace_id": workspace_id, "storage_backend": storage.name}


def get_artifact(artifact_id: str, workspace_id: str = "default", *, include_protected: bool = False) -> tuple[ArtifactRecord, bytes] | None:
    with Session(engine) as session:
        row = session.scalar(select(ArtifactRecord).where(ArtifactRecord.artifact_id == artifact_id, ArtifactRecord.workspace_id == workspace_id))
        if not row:
            return None
        if is_protected_artifact(row) and not include_protected:
            return None
        session.expunge(row)
    data = read_artifact_uri(row.path)
    if data is None:
        return None
    if hashlib.sha256(data).hexdigest() != row.sha256:
        raise RuntimeError(f"Artifact integrity check failed for {artifact_id}")
    return row, data


def delete_artifact(artifact_id: str, workspace_id: str = "default") -> bool:
    with Session(engine) as session:
        row = session.scalar(select(ArtifactRecord).where(ArtifactRecord.artifact_id == artifact_id, ArtifactRecord.workspace_id == workspace_id))
        if not row:
            return False
        path = row.path
        session.delete(row)
        session.commit()
    delete_artifact_uri(path)
    return True


def list_artifacts(limit: int = 100, workspace_id: str = "default", *, include_protected: bool = False) -> list[dict]:
    with Session(engine) as session:
        rows = session.scalars(select(ArtifactRecord).where(ArtifactRecord.workspace_id == workspace_id).order_by(ArtifactRecord.created_at.desc()).limit(limit * 3 if not include_protected else limit)).all()
    if not include_protected:
        rows = [row for row in rows if not is_protected_artifact(row)][:limit]
    else:
        rows = rows[:limit]
    return [{"artifact_id": r.artifact_id, "name": r.name, "media_type": r.media_type, "sha256": r.sha256, "size_bytes": r.size_bytes, "storage_backend": artifact_metadata(r).get("storage_backend", "legacy-local"), "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
