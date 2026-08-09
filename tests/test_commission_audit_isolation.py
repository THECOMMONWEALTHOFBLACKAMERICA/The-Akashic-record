from backend.app.commission_audit import case_audit_events
from backend.app.control import audit, audit_tail, ensure_default_workspace


def test_commission_events_hidden_from_generic_audit_but_visible_per_case():
    ensure_default_workspace()
    case_id = "audit-case-test"
    audit("commission.case_created", "commission_case", case_id, {"case_id": case_id}, workspace_id="default", actor="pytest")
    audit("ordinary.test_event", "test", "ordinary", {}, workspace_id="default", actor="pytest")

    generic = audit_tail(100, workspace_id="default")
    assert all(not event["action"].startswith("commission.") for event in generic)
    assert any(event["action"] == "ordinary.test_event" for event in generic)

    case_events = case_audit_events(case_id, "default", 100)
    assert any(event["action"] == "commission.case_created" for event in case_events)
    assert all(event["action"].startswith("commission.") for event in case_events)
