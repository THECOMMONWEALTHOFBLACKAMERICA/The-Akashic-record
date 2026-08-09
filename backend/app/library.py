from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .bootstrap import schema_bootstrap_enabled
from .memory import Base, engine


class LibraryEntry(Base):
    __tablename__ = "library_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    locator_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


if schema_bootstrap_enabled():
    Base.metadata.create_all(engine)


def upsert_entry(
    workspace_id: str,
    document_id: str,
    *,
    favorite: bool | None = None,
    progress: float | None = None,
    locator: dict | None = None,
    notes: str | None = None,
) -> dict:
    if progress is not None and not 0.0 <= progress <= 1.0:
        raise ValueError("progress must be between 0 and 1")
    with Session(engine) as session:
        row = session.scalar(
            select(LibraryEntry).where(
                LibraryEntry.workspace_id == workspace_id,
                LibraryEntry.document_id == document_id,
            )
        )
        if row is None:
            row = LibraryEntry(workspace_id=workspace_id, document_id=document_id)
            session.add(row)
        if favorite is not None:
            row.favorite = favorite
        if progress is not None:
            row.progress = progress
        if locator is not None:
            row.locator_json = json.dumps(locator, ensure_ascii=False)
        if notes is not None:
            row.notes = notes[:20_000]
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(row)
        return _serialize(row)


def get_entry(workspace_id: str, document_id: str) -> dict | None:
    with Session(engine) as session:
        row = session.scalar(
            select(LibraryEntry).where(
                LibraryEntry.workspace_id == workspace_id,
                LibraryEntry.document_id == document_id,
            )
        )
        return _serialize(row) if row else None


def list_entries(workspace_id: str, limit: int = 200, favorites_only: bool = False) -> list[dict]:
    with Session(engine) as session:
        stmt = select(LibraryEntry).where(LibraryEntry.workspace_id == workspace_id)
        if favorites_only:
            stmt = stmt.where(LibraryEntry.favorite.is_(True))
        rows = session.scalars(stmt.order_by(LibraryEntry.updated_at.desc()).limit(limit)).all()
        return [_serialize(row) for row in rows]


def _serialize(row: LibraryEntry) -> dict:
    return {
        "document_id": row.document_id,
        "workspace_id": row.workspace_id,
        "favorite": row.favorite,
        "progress": row.progress,
        "locator": json.loads(row.locator_json or "{}"),
        "notes": row.notes,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
