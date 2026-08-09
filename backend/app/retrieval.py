from __future__ import annotations

import math
import os
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .ingestion import ChunkRecord, DocumentRecord
from .memory import MemoryRecord, engine
from .semantic import enabled as semantic_enabled, score_many

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


def _scan_limit() -> int:
    try:
        value = int(os.getenv("TAR_SEMANTIC_SCAN_LIMIT", "1500"))
    except ValueError:
        value = 1500
    return max(100, min(value, 5000))


def _combined(lexical: float, semantic: float, confidence: float = 0.5) -> float:
    lexical_component = min(max(lexical, 0.0), 8.0)
    semantic_component = max(semantic, 0.0) * 3.0
    confidence_component = max(0.0, min(confidence, 1.0)) * 0.25
    return lexical_component + semantic_component + confidence_component


def search_chunks(query: str, limit: int = 8, source: str | None = None, workspace_id: str = "default") -> list[dict]:
    with Session(engine) as session:
        stmt = (
            select(ChunkRecord, DocumentRecord)
            .join(DocumentRecord, ChunkRecord.document_id == DocumentRecord.document_id)
            .where(
                DocumentRecord.workspace_id == workspace_id,
                ChunkRecord.workspace_id == workspace_id,
            )
            .order_by(ChunkRecord.id.desc())
        )
        if source:
            stmt = stmt.where(DocumentRecord.source == source)
        rows = session.execute(stmt.limit(_scan_limit())).all()

    texts = [chunk.text for chunk, _ in rows]
    semantic_scores = score_many(query, texts) if semantic_enabled() else [0.0] * len(rows)
    ranked = []
    for (chunk, doc), semantic in zip(rows, semantic_scores):
        lexical = _bm25ish(query, chunk.text)
        if lexical <= 0 and semantic < 0.15:
            continue
        score = _combined(lexical, semantic)
        ranked.append((score, lexical, semantic, chunk, doc))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "kind": "chunk",
            "document_id": doc.document_id,
            "chunk_id": chunk.id,
            "source": doc.source,
            "title": doc.title,
            "url": doc.source_uri,
            "snippet": chunk.text[:1800],
            "page": chunk.page,
            "retrieval_score": round(score, 4),
            "lexical_score": round(lexical, 4),
            "semantic_score": round(semantic, 4),
            "retrieval_method": "semantic+lexical" if semantic_enabled() else "lexical",
            "sha256": doc.sha256,
        }
        for score, lexical, semantic, chunk, doc in ranked[:limit]
    ]


def _memory_candidates(query: str, limit: int, source: str | None, workspace_id: str) -> list[dict]:
    with Session(engine) as session:
        stmt = (
            select(MemoryRecord)
            .where(MemoryRecord.workspace_id == workspace_id)
            .order_by(MemoryRecord.created_at.desc())
            .limit(_scan_limit())
        )
        if source:
            stmt = stmt.where(MemoryRecord.source == source)
        rows = session.scalars(stmt).all()

    texts = [" ".join([row.title, row.snippet, row.body]) for row in rows]
    semantic_scores = score_many(query, texts) if semantic_enabled() else [0.0] * len(rows)
    ranked = []
    for row, text, semantic in zip(rows, texts, semantic_scores):
        lexical = _bm25ish(query, text)
        if lexical <= 0 and semantic < 0.15:
            continue
        score = _combined(lexical, semantic, row.confidence)
        ranked.append((score, lexical, semantic, row))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "kind": "memory",
            "id": row.id,
            "source": row.source,
            "title": row.title,
            "url": row.url,
            "snippet": row.snippet or row.body[:1200],
            "confidence": row.confidence,
            "retrieval_score": round(score, 4),
            "lexical_score": round(lexical, 4),
            "semantic_score": round(semantic, 4),
            "retrieval_method": "semantic+lexical" if semantic_enabled() else "lexical",
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for score, lexical, semantic, row in ranked[:limit]
    ]


def hybrid_recall(query: str, limit: int = 10, source: str | None = None, workspace_id: str = "default") -> list[dict]:
    candidate_limit = max(limit * 3, 20)
    chunks = search_chunks(query, candidate_limit, source=source, workspace_id=workspace_id)
    memories = _memory_candidates(query, candidate_limit, source, workspace_id)
    merged = [(float(item["retrieval_score"]), item) for item in chunks + memories]

    seen: set[tuple] = set()
    out = []
    for _, item in sorted(merged, key=lambda x: x[0], reverse=True):
        key = (
            item.get("document_id"),
            item.get("chunk_id"),
            item.get("source"),
            item.get("url"),
            item.get("title"),
            item.get("snippet"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out
