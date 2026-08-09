from __future__ import annotations

import hashlib
import os
from functools import lru_cache

import numpy as np

_MODEL_ERROR = ""


@lru_cache(maxsize=1)
def _model():
    global _MODEL_ERROR
    model_name = os.getenv("TAR_EMBEDDING_MODEL", "").strip()
    semantic_on = os.getenv("TAR_ENABLE_SEMANTIC_RETRIEVAL", "false").lower() in {"1", "true", "yes"}
    if not semantic_on or not model_name:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        _MODEL_ERROR = ""
        return model
    except Exception as exc:
        # Retrieval must remain usable even when an optional embedding model is unavailable.
        _MODEL_ERROR = str(exc)
        return None


@lru_cache(maxsize=4096)
def _cached_vector(model_name: str, digest: str, text: str) -> tuple[float, ...]:
    model = _model()
    if model is None:
        return ()
    vector = model.encode(text, normalize_embeddings=True)
    return tuple(float(x) for x in vector)


def enabled() -> bool:
    return _model() is not None


def status() -> dict:
    requested = os.getenv("TAR_ENABLE_SEMANTIC_RETRIEVAL", "false").lower() in {"1", "true", "yes"}
    model_name = os.getenv("TAR_EMBEDDING_MODEL", "").strip()
    active = enabled()
    return {
        "requested": requested,
        "model": model_name,
        "active": active,
        "error": _MODEL_ERROR if requested and not active else "",
    }


def score_many(query: str, texts: list[str]) -> list[float]:
    """Return cosine similarity scores, falling back to zeros when disabled.

    Candidate vectors are cached by content hash inside each process. At larger
    scale this interface can be replaced with pgvector or a dedicated vector
    service without changing retrieval callers.
    """
    model = _model()
    model_name = os.getenv("TAR_EMBEDDING_MODEL", "").strip()
    if model is None or not texts:
        return [0.0] * len(texts)

    try:
        query_vec = np.asarray(model.encode(query, normalize_embeddings=True), dtype=np.float32)
        scores: list[float] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
            vec = _cached_vector(model_name, digest, text)
            if not vec:
                scores.append(0.0)
                continue
            score = float(np.dot(query_vec, np.asarray(vec, dtype=np.float32)))
            scores.append(max(-1.0, min(1.0, score)))
        return scores
    except Exception:
        return [0.0] * len(texts)
