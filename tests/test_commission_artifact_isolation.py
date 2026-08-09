from backend.app.artifacts import get_artifact, list_artifacts, save_artifact


def test_protected_commission_artifact_hidden_from_generic_access():
    artifact = save_artifact(
        "protected-record.pdf",
        b"protected bytes",
        "application/pdf",
        {"classification": "commission_original_evidence", "case_id": "case-a", "public_ipfs_allowed": False},
        "default",
    )
    assert get_artifact(artifact["artifact_id"], "default") is None
    protected = get_artifact(artifact["artifact_id"], "default", include_protected=True)
    assert protected is not None
    assert artifact["artifact_id"] not in {row["artifact_id"] for row in list_artifacts(500, "default")}
