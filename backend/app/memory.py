from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .settings import settings


class Base(DeclarativeBase):
    pass


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(1000))
    url: Mapped[str] = mapped_column(String(3000), default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


engine = create_engine(settings.database_url, future=True)
Base.metadata.create_all(engine)


def _tokens(text: str) -> set[str]:
    return {t.lower().strip(".,:;!?()[]{}\"'") for t in text.split() if len(t) > 2}


def remember(records: Iterable[dict]) -> int:
    count = 0
    with Session(engine) as session:
        for item in records:
            source = str(item.get("source", "unknown"))
            title = str(item.get("title", "Untitled"))
            url = str(item.get("url", "") or "")
            existing = session.scalar(select(MemoryRecord).where(MemoryRecord.source == source, MemoryRecord.url == url, MemoryRecord.title == title))
            if existing:
                existing.snippet = str(item.get("snippet", existing.snippet) or existing.snippet)
                existing.body = str(item.get("body", existing.body) or existing.body)
                existing.confidence = float(item.get("confidence", existing.confidence) or existing.confidence)
            else:
                session.add(MemoryRecord(source=source, title=title, url=url, snippet=str(item.get("snippet", "") or ""), body=str(item.get("body", "") or ""), confidence=float(item.get("confidence", 0.5) or 0.5)))
                count += 1
        session.commit()
    return count


def recall(query: str, limit: int = 8) -> list[dict]:
    q = _tokens(query)
    if not q:
        return []
    with Session(engine) as session:
        rows = session.scalars(select(MemoryRecord).order_by(MemoryRecord.created_at.desc()).limit(500)).all()
    ranked: list[tuple[float, MemoryRecord]] = []
    for row in rows:
        haystack = _tokens(" ".join([row.title, row.snippet, row.body]))
        overlap = len(q & haystack)
        if overlap:
            ranked.append((overlap / max(len(q), 1), row))
    ranked.sort(key=lambda x: (x[0], x[1].confidence), reverse=True)
    return [{"id": row.id, "source": row.source, "title": row.title, "url": row.url, "snippet": row.snippet or row.body[:1200], "confidence": row.confidence, "memory_score": round(score, 4), "created_at": row.created_at.isoformat() if row.created_at else None} for score, row in ranked[:limit]]


def stats() -> dict:
    with Session(engine) as session:
        rows = session.scalars(select(MemoryRecord)).all()
    by_source: dict[str, int] = {}
    for row in rows:
        by_source[row.source] = by_source.get(row.source, 0) + 1
    return {"records": len(rows), "by_source": by_source}
