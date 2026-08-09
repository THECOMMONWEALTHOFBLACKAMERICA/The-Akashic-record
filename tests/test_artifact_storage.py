import hashlib

import pytest

from backend.app.artifacts import get_artifact, save_artifact
from backend.app.storage import LocalStorage


def test_local_storage_rejects_path_escape(tmp_path):
    storage = LocalStorage(tmp_path)
    outside = tmp_path.parent / "outside.txt"
    outside.write_bytes(b"outside")
    assert storage.get(str(outside)) is None


def test_artifact_round_trip_and_hash(monkeypatch, tmp_path):
    monkeypatch.setenv("TAR_ARTIFACT_BACKEND", "local")
    monkeypatch.setenv("TAR_ARTIFACT_DIR", str(tmp_path))
    payload = b"artifact integrity payload"
    artifact = save_artifact("proof.txt", payload, "text/plain", workspace_id="artifact-alpha")
    found = get_artifact(artifact["artifact_id"], "artifact-alpha")
    assert found is not None
    row, data = found
    assert data == payload
    assert row.sha256 == hashlib.sha256(payload).hexdigest()
    assert get_artifact(artifact["artifact_id"], "artifact-beta") is None


def test_integrity_failure_is_not_silently_served(monkeypatch, tmp_path):
    monkeypatch.setenv("TAR_ARTIFACT_BACKEND", "local")
    monkeypatch.setenv("TAR_ARTIFACT_DIR", str(tmp_path))
    artifact = save_artifact("proof.txt", b"original", "text/plain", workspace_id="artifact-integrity")
    found = get_artifact(artifact["artifact_id"], "artifact-integrity")
    assert found is not None
    row, _ = found
    with open(row.path, "wb") as handle:
        handle.write(b"tampered")
    with pytest.raises(RuntimeError, match="integrity check failed"):
        get_artifact(artifact["artifact_id"], "artifact-integrity")
