from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .artifacts import get_artifact
from .bootstrap import schema_bootstrap_enabled
from .ipfs import add_bytes, manifest_for_artifact, publish_manifest
from .memory import Base, engine
from .version import VERSION


class PublicationRecord(Base):
    __tablename__ = "artifact_publications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    publication_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True)
    artifact_id: Mapped[str] = mapped_column(String(64), index=True)
    artifact_cid: Mapped[str] = mapped_column(String(200), index=True)
    manifest_cid: Mapped[str] = mapped_column(String(200), index=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


if schema_bootstrap_enabled():
    Base.metadata.create_all(engine)


def publish_artifact(artifact_id: str, workspace_id: str) -> dict:
    existing = latest_publication(artifact_id, workspace_id)
    if existing:
        return {**existing, "deduplicated": True}
    found = get_artifact(artifact_id, workspace_id, include_protected=True)
    if not found:
        raise KeyError("artifact not found")
    row, data = found
    metadata = json.loads(row.metadata_json or "{}")
    if metadata.get("classification") == "commission_original_evidence" or metadata.get("public_ipfs_allowed") is False:
        raise PermissionError("artifact is classified as protected Commission evidence and cannot be published to public IPFS")
    artifact_ipfs = add_bytes(data, row.name, row.media_type)
    manifest = manifest_for_artifact(artifact_id=row.artifact_id, workspace_id=row.workspace_id, name=row.name, media_type=row.media_type, sha256=row.sha256, size_bytes=row.size_bytes, artifact_cid=artifact_ipfs["cid"], version=VERSION)
    manifest_ipfs = publish_manifest(manifest)
    publication_id = uuid.uuid4().hex
    with Session(engine) as session:
        session.add(PublicationRecord(publication_id=publication_id, workspace_id=workspace_id, artifact_id=artifact_id, artifact_cid=artifact_ipfs["cid"], manifest_cid=manifest_ipfs["cid"], sha256=row.sha256))
        session.commit()
    return {"publication_id": publication_id, "workspace_id": workspace_id, "artifact_id": artifact_id, "artifact_cid": artifact_ipfs["cid"], "artifact_gateway_url": artifact_ipfs["gateway_url"], "manifest_cid": manifest_ipfs["cid"], "manifest_gateway_url": manifest_ipfs["gateway_url"], "sha256": row.sha256, "deduplicated": False}


def latest_publication(artifact_id: str, workspace_id: str) -> dict | None:
    with Session(engine) as session:
        row = session.scalar(select(PublicationRecord).where(PublicationRecord.artifact_id == artifact_id, PublicationRecord.workspace_id == workspace_id).order_by(PublicationRecord.id.desc()).limit(1))
        return _serialize(row) if row else None


def list_publications(workspace_id: str, limit: int = 100) -> list[dict]:
    with Session(engine) as session:
        rows = session.scalars(select(PublicationRecord).where(PublicationRecord.workspace_id == workspace_id).order_by(PublicationRecord.id.desc()).limit(limit)).all()
    return [_serialize(row) for row in rows]


def _serialize(row: PublicationRecord) -> dict:
    from .ipfs import gateway_url
    return {"publication_id": row.publication_id, "workspace_id": row.workspace_id, "artifact_id": row.artifact_id, "artifact_cid": row.artifact_cid, "artifact_gateway_url": f"{gateway_url()}/{row.artifact_cid}", "manifest_cid": row.manifest_cid, "manifest_gateway_url": f"{gateway_url()}/{row.manifest_cid}", "sha256": row.sha256, "created_at": row.created_at.isoformat() if row.created_at else None}
