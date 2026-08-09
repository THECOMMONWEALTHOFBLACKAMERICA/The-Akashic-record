import pytest

from backend.app.commission import EVIDENCE_STATUSES, add_evidence, create_case, delete_case, review_evidence, update_case
from backend.app.control import ensure_default_workspace


def test_commission_case_evidence_and_legal_hold():
    ensure_default_workspace()
    case = create_case("default", application_ref="TEST-CASE", applicant_label="Test Applicant", actor="pytest")
    evidence = add_evidence(
        case["case_id"],
        "default",
        title="1870 census record",
        source_tier=1,
        source="national_archives",
        original_filename="record.pdf",
        original_bytes=b"test primary record bytes",
        uploader="pytest",
        actor="pytest",
    )
    assert evidence["status"] == "unverified"
    assert len(evidence["original_sha256"]) == 64

    reviewed = review_evidence(evidence["evidence_id"], "default", status="verified", reviewer="commissioner", review_notes="Underlying record reviewed.")
    assert reviewed["status"] == "verified"
    assert reviewed["reviewer"] == "commissioner"

    update_case(case["case_id"], "default", legal_hold=True, actor="commissioner")
    with pytest.raises(PermissionError):
        delete_case(case["case_id"], "default", actor="commissioner", policy_basis="test retention schedule")

    update_case(case["case_id"], "default", legal_hold=False, actor="commissioner")
    result = delete_case(case["case_id"], "default", actor="commissioner", policy_basis="test cleanup")
    assert result["deleted"] is True


def test_excluded_evidence_requires_reason():
    ensure_default_workspace()
    case = create_case("default", application_ref="TEST-EXCLUDED", actor="pytest")
    evidence = add_evidence(case["case_id"], "default", title="Unreliable page", source_tier=2, actor="pytest")
    with pytest.raises(ValueError):
        review_evidence(evidence["evidence_id"], "default", status="excluded", reviewer="commissioner")
    delete_case(case["case_id"], "default", actor="pytest", policy_basis="test cleanup")


def test_evidence_status_vocabulary():
    assert EVIDENCE_STATUSES == {"verified", "corroborated", "conflicting", "unverified", "insufficient", "excluded"}
