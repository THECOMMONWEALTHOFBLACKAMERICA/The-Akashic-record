from backend.app.artifacts import get_artifact, list_artifacts, save_artifact
from backend.app.ingestion import ingest_bytes, list_documents
from backend.app.memory import recall, remember
from backend.app.retrieval import hybrid_recall


def test_memory_isolation():
    remember([{"source":"test","title":"Private Alpha","url":"urn:alpha","snippet":"workspace alpha secret phrase"}], workspace_id="alpha")
    assert recall("secret phrase", workspace_id="alpha")
    assert not any(x["title"] == "Private Alpha" for x in recall("secret phrase", workspace_id="beta"))


def test_document_isolation():
    ingest_bytes("alpha.txt", b"unique alpha archival evidence", title="Alpha Archive", workspace_id="alpha")
    assert any(d["title"] == "Alpha Archive" for d in list_documents(workspace_id="alpha"))
    assert not any(d["title"] == "Alpha Archive" for d in list_documents(workspace_id="beta"))
    assert any(x.get("title") == "Alpha Archive" for x in hybrid_recall("unique alpha archival evidence", workspace_id="alpha"))
    assert not any(x.get("title") == "Alpha Archive" for x in hybrid_recall("unique alpha archival evidence", workspace_id="beta"))


def test_artifact_isolation():
    artifact = save_artifact("private.txt", b"private", "text/plain", workspace_id="alpha")
    assert get_artifact(artifact["artifact_id"], "alpha") is not None
    assert get_artifact(artifact["artifact_id"], "beta") is None
    assert any(x["artifact_id"] == artifact["artifact_id"] for x in list_artifacts(workspace_id="alpha"))
