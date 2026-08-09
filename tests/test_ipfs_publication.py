import pytest

from backend.app.artifacts import save_artifact
from backend.app.ipfs import IPFSPublicationDisabled, manifest_for_artifact
from backend.app import publications


def test_ipfs_publication_is_off_by_default(monkeypatch):
    monkeypatch.delenv("TAR_ENABLE_PUBLIC_IPFS", raising=False)
    from backend.app.ipfs import add_bytes

    with pytest.raises(IPFSPublicationDisabled):
        add_bytes(b"private", "private.txt", "text/plain")


def test_manifest_binds_cid_and_hash():
    manifest = manifest_for_artifact(
        artifact_id="artifact-1",
        workspace_id="workspace-1",
        name="proof.txt",
        media_type="text/plain",
        sha256="a" * 64,
        size_bytes=12,
        artifact_cid="bafy-test",
        version="test-version",
    )
    assert manifest["schema"] == "tar.provenance.artifact.v1"
    assert manifest["artifact_cid"] == "bafy-test"
    assert manifest["sha256"] == "a" * 64


def test_publication_records_artifact_and_manifest_cids(monkeypatch, tmp_path):
    monkeypatch.setenv("TAR_ARTIFACT_BACKEND", "local")
    monkeypatch.setenv("TAR_ARTIFACT_DIR", str(tmp_path))
    artifact = save_artifact("proof.txt", b"public proof", "text/plain", workspace_id="ipfs-test")

    calls = []

    def fake_add(data, filename, media_type="application/octet-stream"):
        calls.append((data, filename, media_type))
        return {"cid": "bafy-artifact", "gateway_url": "https://gateway.invalid/ipfs/bafy-artifact"}

    def fake_manifest(manifest):
        assert manifest["artifact_cid"] == "bafy-artifact"
        return {"cid": "bafy-manifest", "gateway_url": "https://gateway.invalid/ipfs/bafy-manifest"}

    monkeypatch.setattr(publications, "add_bytes", fake_add)
    monkeypatch.setattr(publications, "publish_manifest", fake_manifest)
    result = publications.publish_artifact(artifact["artifact_id"], "ipfs-test")
    assert result["artifact_cid"] == "bafy-artifact"
    assert result["manifest_cid"] == "bafy-manifest"
    assert len(calls) == 1

    second = publications.publish_artifact(artifact["artifact_id"], "ipfs-test")
    assert second["deduplicated"] is True
