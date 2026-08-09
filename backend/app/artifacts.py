from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .memory import Base, engine
from .schema import ensure_workspace_columns


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


Base.metadata.create_all(engine)
ensure_workspace_columns(engine)


def artifact_root() -> Path:
    root = Path(os.getenv("TAR_ARTIFACT_DIR", "./artifacts")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_artifact(name: str, data: bytes, media_type: str, metadata: dict | None = None, workspace_id: str = "default") -> dict:
    artifact_id = uuid.uuid4().hex
    safe = "".join(c for c in Path(name).name if c.isalnum() or c in "._-") or artifact_id
    workspace_dir = artifact_root() / workspace_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    path = workspace_dir / f"{artifact_id}-{safe}"
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    with Session(engine) as session:
        session.add(ArtifactRecord(artifact_id=artifact_id, workspace_id=workspace_id, name=safe, media_type=media_type, path=str(path), sha256=digest, size_bytes=len(data), metadata_json=json.dumps(metadata or {}, ensure_ascii=False)))
        session.commit()
    return {"artifact_id": artifact_id, "name": safe, "media_type": media_type, "sha256": digest, "size_bytes": len(data), "workspace_id": workspace_id}


def get_artifact(artifact_id: str, workspace_id: str = "default") -> tuple[ArtifactRecord, bytes] | None:
    with Session(engine) as session:
        row = session.scalar(select(ArtifactRecord).where(ArtifactRecord.artifact_id == artifact_id, ArtifactRecord.workspace_id == workspace_id))
        if not row: return None
        session.expunge(row)
    path = Path(row.path)
    if not path.exists(): return None
    return row, path.read_bytes()


def list_artifacts(limit: int = 100, workspace_id: str = "default") -> list[dict]:
    with Session(engine) as session:
        rows = session.scalars(select(ArtifactRecord).where(ArtifactRecord.workspace_id == workspace_id).order_by(ArtifactRecord.created_at.desc()).limit(limit)).all()
    return [{"artifact_id": r.artifact_id, "name": r.name, "media_type": r.media_type, "sha256": r.sha256, "size_bytes": r.size_bytes, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
