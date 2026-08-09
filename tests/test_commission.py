import pytest

from backend.app.artifacts import get_artifact, save_artifact
from backend.app.commission import EVIDENCE_STATUSES, add_evidence, create_case, update_case
from backend.app.commission_retention import delete_case_with_retention
from backend.app.commission_review import review_and_retier_evidence
from backend.app.control import ensure_default_workspace


def test_commission_case_evidence_review_retier_and_legal_hold():
    ensure_default_workspace()
    case = create_case("default", application_ref="TEST-CASE", applicant_label="Test Applicant", actor="pytest")
    original = save_artifact(
        "record.pdf",
        b"test primary record bytes",
        "application/pdf",
        {"classification": "commission_original_evidence", "case_id": case["case_id"], "public_ipfs_allowed": False},
        "default",
    )
    evidence = add_evidence(
        case["case_id"],
        "default",
        title="1870 census record",
        source_tier=2,
        source="national_archives",
        retrieval_metadata={"original_artifact_id": original["artifact_id"]},
        original_filename="record.pdf",
        original_bytes=b"test primary record bytes",
        uploader="pytest",
        actor="pytest",
    )
    assert evidence["status"] == "unverified"
    assert len(evidence["original_sha256"]) == 64

    reviewed = review_and_retier_evidence(
        evidence["evidence_id"],
        "default",
        status="verified",
        source_tier=1,
        reviewer="commissioner",
        review_notes="Underlying government record reviewed.",
    )
    assert reviewed["status"] == "verified"
    assert reviewed["source_tier"] == 1
    assert reviewed["reviewer"] == "commissioner"

    update_case(case["case_id"], "default", legal_hold=True, actor="commissioner")
    with pytest.raises(PermissionError):
        delete_case_with_retention(case["case_id"], "default", actor="commissioner", policy_basis="test retention schedule")
    assert get_artifact(original["artifact_id"], "default") is not None

    update_case(case["case_id"], "default", legal_hold=False, actor="commissioner")
    result = delete_case_with_retention(case["case_id"], "default", actor="commissioner", policy_basis="test cleanup")
    assert result["deleted"] is True
    assert result["complete"] is True
    assert original["artifact_id"] in result["artifacts_deleted"]
    assert get_artifact(original["artifact_id"], "default") is None


def test_excluded_evidence_requires_reason():
    ensure_default_workspace()
    case = create_case("default", application_ref="TEST-EXCLUDED", actor="pytest")
    evidence = add_evidence(case["case_id"], "default", title="Unreliable page", source_tier=2, actor="pytest")
    with pytest.raises(ValueError):
        review_and_retier_evidence(evidence["evidence_id"], "default", status="excluded", reviewer="commissioner")
    result = delete_case_with_retention(case["case_id"], "default", actor="pytest", policy_basis="test cleanup")
    assert result["deleted"] is True


def test_evidence_status_vocabulary():
    assert EVIDENCE_STATUSES == {"verified", "corroborated", "conflicting", "unverified", "insufficient", "excluded"}
