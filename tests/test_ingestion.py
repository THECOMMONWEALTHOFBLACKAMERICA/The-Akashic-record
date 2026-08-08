from backend.app.ingestion import ingest_bytes, list_documents
from backend.app.retrieval import hybrid_recall


def test_text_ingestion_and_recall():
    payload = b"The Freedmen's Bureau was established in 1865. This test record mentions Reconstruction and education."
    result = ingest_bytes("freedmen-note.txt", payload, title="Freedmen Test", source="test_archive")
    assert result["status"] in {"completed", "deduplicated"}
    assert result["document_id"]
    hits = hybrid_recall("Freedmen Bureau Reconstruction education", limit=5)
    assert any(x.get("title") == "Freedmen Test" for x in hits)


def test_csv_ingestion():
    data = b"name,roll,tribe\nJane Doe,1234,Example Nation\nJohn Doe,5678,Example Nation\n"
    result = ingest_bytes("rolls.csv", data, title="Roll Test", source="test_rolls")
    assert result["status"] in {"completed", "deduplicated"}
    docs = list_documents()
    assert any(d["title"] == "Roll Test" for d in docs)
