from __future__ import annotations

import hashlib
import os
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def _model():
    model_name = os.getenv("TAR_EMBEDDING_MODEL", "").strip()
    enabled = os.getenv("TAR_ENABLE_SEMANTIC_RETRIEVAL", "false").lower() in {"1", "true", "yes"}
    if not enabled or not model_name:
        return None
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


@lru_cache(maxsize=4096)
def _cached_vector(model_name: str, digest: str, text: str) -> tuple[float, ...]:
    model = _model()
    if model is None:
        return ()
    vector = model.encode(text, normalize_embeddings=True)
    return tuple(float(x) for x in vector)


def enabled() -> bool:
    return _model() is not None


def score_many(query: str, texts: list[str]) -> list[float]:
    """Return cosine similarity scores for texts.

    Embeddings are lazy and optional so deployments without a local embedding
    model keep deterministic lexical retrieval. Candidate vectors are cached by
    content hash inside each worker process.
    """
    model = _model()
    model_name = os.getenv("TAR_EMBEDDING_MODEL", "").strip()
    if model is None or not texts:
        return [0.0] * len(texts)

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
