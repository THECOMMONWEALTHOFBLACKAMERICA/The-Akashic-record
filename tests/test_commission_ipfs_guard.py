import pytest

from backend.app.artifacts import save_artifact
from backend.app.publications import publish_artifact


def test_commission_original_artifact_cannot_publish_to_ipfs():
    artifact = save_artifact(
        "applicant-record.pdf",
        b"protected applicant record",
        "application/pdf",
        {"classification": "commission_original_evidence", "public_ipfs_allowed": False},
        "default",
    )
    with pytest.raises(PermissionError):
        publish_artifact(artifact["artifact_id"], "default")
