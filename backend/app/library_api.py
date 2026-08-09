from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_identity
from .control import audit
from .ingestion import DocumentRecord
from .library import get_entry, list_entries, upsert_entry
from .memory import engine
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/v1/library", tags=["library"])


class LibraryUpdate(BaseModel):
    favorite: bool | None = None
    progress: float | None = Field(default=None, ge=0.0, le=1.0)
    locator: dict | None = None
    notes: str | None = Field(default=None, max_length=20_000)


def _document_exists(workspace_id: str, document_id: str) -> bool:
    with Session(engine) as session:
        return session.scalar(select(DocumentRecord.id).where(DocumentRecord.workspace_id == workspace_id, DocumentRecord.document_id == document_id)) is not None


@router.get("")
def library(limit: int = 200, favorites_only: bool = False, identity: dict = Depends(require_identity)):
    return {"entries": list_entries(identity["workspace_id"], max(1, min(limit, 500)), favorites_only)}


@router.get("/{document_id}")
def library_entry(document_id: str, identity: dict = Depends(require_identity)):
    entry = get_entry(identity["workspace_id"], document_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Library entry not found")
    return entry


@router.put("/{document_id}")
def library_update(document_id: str, req: LibraryUpdate, identity: dict = Depends(require_identity)):
    workspace_id = identity["workspace_id"]
    if not _document_exists(workspace_id, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        result = upsert_entry(
            workspace_id,
            document_id,
            favorite=req.favorite,
            progress=req.progress,
            locator=req.locator,
            notes=req.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit("library.updated", "document", document_id, {"favorite": req.favorite, "progress": req.progress}, workspace_id=workspace_id, actor=identity["label"])
    return result
