import uuid

from backend.app.library import get_entry, list_entries, upsert_entry


def test_library_progress_and_favorite_are_workspace_scoped():
    doc_id = "doc-" + uuid.uuid4().hex
    alpha = "alpha-" + uuid.uuid4().hex
    beta = "beta-" + uuid.uuid4().hex

    entry = upsert_entry(alpha, doc_id, favorite=True, progress=0.42, locator={"chapter": 3}, notes="review this source")
    assert entry["favorite"] is True
    assert entry["progress"] == 0.42
    assert entry["locator"]["chapter"] == 3
    assert get_entry(beta, doc_id) is None
    assert any(x["document_id"] == doc_id for x in list_entries(alpha))
    assert not any(x["document_id"] == doc_id for x in list_entries(beta))
