from backend.app import retrieval
from backend.app.ingestion import ingest_bytes


def test_semantic_signal_can_retrieve_without_keyword_overlap(monkeypatch):
    workspace = "semantic-test-workspace"
    ingest_bytes(
        "concept.txt",
        b"A crimson falcon circles above a silent canyon at dawn.",
        title="Conceptual Record",
        workspace_id=workspace,
    )

    monkeypatch.setattr(retrieval, "semantic_enabled", lambda: True)
    monkeypatch.setattr(retrieval, "score_many", lambda query, texts: [0.91 for _ in texts])

    results = retrieval.search_chunks(
        "completely unrelated vocabulary",
        limit=5,
        workspace_id=workspace,
    )
    assert results
    assert results[0]["semantic_score"] == 0.91
    assert results[0]["retrieval_method"] == "semantic+lexical"
