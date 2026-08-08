from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import fitz
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .memory import Base, engine


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(1000))
    source: Mapped[str] = mapped_column(String(100), index=True)
    source_uri: Mapped[str] = mapped_column(String(3000), default="")
    media_type: Mapped[str] = mapped_column(String(100), default="text/plain")
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ChunkRecord(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.document_id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    start_char: Mapped[int] = mapped_column(Integer, default=0)
    end_char: Mapped[int] = mapped_column(Integer, default=0)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default="queued")
    title: Mapped[str] = mapped_column(String(1000), default="")
    source: Mapped[str] = mapped_column(String(100), default="upload")
    document_id: Mapped[str] = mapped_column(String(64), default="")
    chunks: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Base.metadata.create_all(engine)


def _sha256(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def _chunk_text(text: str, size: int = 1400, overlap: int = 220) -> list[tuple[int, int, str]]:
    text = text.replace("\x00", " ").strip()
    if not text:
        return []
    chunks: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind("\n", start + size // 2, end), text.rfind(". ", start + size // 2, end))
            if boundary > start:
                end = boundary + 1
        part = text[start:end].strip()
        if part:
            chunks.append((start, end, part))
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _pdf_text(data: bytes) -> list[tuple[int | None, str]]:
    doc = fitz.open(stream=data, filetype="pdf")
    return [(i + 1, page.get_text("text")) for i, page in enumerate(doc)]


def _tabular_text(data: bytes, suffix: str) -> str:
    decoded = data.decode("utf-8-sig", errors="replace")
    if suffix == ".json":
        obj = json.loads(decoded)
        if isinstance(obj, list):
            return "\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in obj)
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    rows = csv.DictReader(io.StringIO(decoded))
    return "\n".join(" | ".join(f"{k}: {v}" for k, v in row.items()) for row in rows)


def parse_bytes(filename: str, data: bytes) -> tuple[str, list[tuple[int | None, str]]]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "application/pdf", _pdf_text(data)
    if suffix in {".csv", ".json"}:
        return ("application/json" if suffix == ".json" else "text/csv"), [(None, _tabular_text(data, suffix))]
    return "text/plain", [(None, data.decode("utf-8", errors="replace"))]


def ingest_bytes(filename: str, data: bytes, *, title: str | None = None, source: str = "upload", source_uri: str = "", metadata: dict | None = None) -> dict:
    job_id = uuid.uuid4().hex
    digest = _sha256(data)
    with Session(engine) as session:
        existing = session.scalar(select(DocumentRecord).where(DocumentRecord.sha256 == digest))
        if existing:
            count = len(session.scalars(select(ChunkRecord).where(ChunkRecord.document_id == existing.document_id)).all())
            return {"job_id": job_id, "status": "deduplicated", "document_id": existing.document_id, "chunks": count}
        job = IngestJob(id=job_id, status="processing", title=title or filename, source=source)
        session.add(job)
        session.commit()

    try:
        media_type, page_texts = parse_bytes(filename, data)
        document_id = uuid.uuid4().hex
        chunk_rows: list[ChunkRecord] = []
        ordinal = 0
        for page, text in page_texts:
            for start, end, chunk in _chunk_text(text):
                chunk_rows.append(ChunkRecord(document_id=document_id, ordinal=ordinal, text=chunk, start_char=start, end_char=end, page=page, metadata_json=json.dumps({"filename": filename, **(metadata or {})}, ensure_ascii=False)))
                ordinal += 1
        with Session(engine) as session:
            session.add(DocumentRecord(document_id=document_id, title=title or filename, source=source, source_uri=source_uri, media_type=media_type, sha256=digest, metadata_json=json.dumps(metadata or {}, ensure_ascii=False)))
            session.add_all(chunk_rows)
            job = session.get(IngestJob, job_id)
            job.status = "completed"
            job.document_id = document_id
            job.chunks = len(chunk_rows)
            job.finished_at = datetime.now(timezone.utc)
            session.commit()
        return {"job_id": job_id, "status": "completed", "document_id": document_id, "chunks": len(chunk_rows), "sha256": digest}
    except Exception as exc:
        with Session(engine) as session:
            job = session.get(IngestJob, job_id)
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            session.commit()
        raise


def get_job(job_id: str) -> dict | None:
    with Session(engine) as session:
        job = session.get(IngestJob, job_id)
        if not job:
            return None
        return {"id": job.id, "status": job.status, "title": job.title, "source": job.source, "document_id": job.document_id, "chunks": job.chunks, "error": job.error, "created_at": job.created_at.isoformat() if job.created_at else None, "finished_at": job.finished_at.isoformat() if job.finished_at else None}


def list_documents(limit: int = 100) -> list[dict]:
    with Session(engine) as session:
        docs = session.scalars(select(DocumentRecord).order_by(DocumentRecord.created_at.desc()).limit(limit)).all()
    return [{"document_id": d.document_id, "title": d.title, "source": d.source, "source_uri": d.source_uri, "media_type": d.media_type, "sha256": d.sha256, "created_at": d.created_at.isoformat() if d.created_at else None} for d in docs]
