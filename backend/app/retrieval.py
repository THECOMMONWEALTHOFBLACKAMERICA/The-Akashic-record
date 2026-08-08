from __future__ import annotations

import math
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .ingestion import ChunkRecord, DocumentRecord
from .memory import engine, recall

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'_-]+")


def _tokens(text: str) -> list[str]:
    return [x.lower() for x in _TOKEN_RE.findall(text or "") if len(x) > 2]


def _bm25ish(query: str, text: str) -> float:
    q = Counter(_tokens(query))
    d = Counter(_tokens(text))
    if not q or not d:
        return 0.0
    overlap = 0.0
    length_norm = 1.0 + math.log1p(sum(d.values())) / 8.0
    for token, weight in q.items():
        tf = d.get(token, 0)
        if tf:
            overlap += weight * (1.0 + math.log1p(tf))
    return overlap / length_norm


def search_chunks(query: str, limit: int = 8, source: str | None = None) -> list[dict]:
    with Session(engine) as session:
        stmt = select(ChunkRecord, DocumentRecord).join(DocumentRecord, ChunkRecord.document_id == DocumentRecord.document_id)
        if source:
            stmt = stmt.where(DocumentRecord.source == source)
        rows = session.execute(stmt.limit(5000)).all()
    ranked = []
    for chunk, doc in rows:
        lexical = _bm25ish(query, chunk.text)
        if lexical <= 0:
            continue
        ranked.append((lexical, chunk, doc))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [{
        "kind": "chunk",
        "document_id": doc.document_id,
        "chunk_id": chunk.id,
        "source": doc.source,
        "title": doc.title,
        "url": doc.source_uri,
        "snippet": chunk.text[:1800],
        "page": chunk.page,
        "retrieval_score": round(score, 4),
        "sha256": doc.sha256,
    } for score, chunk, doc in ranked[:limit]]


def hybrid_recall(query: str, limit: int = 10, source: str | None = None) -> list[dict]:
    chunks = search_chunks(query, max(limit * 2, 10), source=source)
    memories = recall(query, max(limit * 2, 10))
    merged: list[tuple[float, dict]] = []
    for item in chunks:
        merged.append((float(item.get("retrieval_score", 0.0)), item))
    for item in memories:
        if source and item.get("source") != source:
            continue
        score = float(item.get("memory_score", 0.0)) * 3.0 + float(item.get("confidence", 0.5))
        merged.append((score, {"kind": "memory", **item, "retrieval_score": round(score, 4)}))
    seen: set[tuple] = set()
    out = []
    for _, item in sorted(merged, key=lambda x: x[0], reverse=True):
        key = (item.get("document_id"), item.get("chunk_id"), item.get("source"), item.get("url"), item.get("title"), item.get("snippet"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out
