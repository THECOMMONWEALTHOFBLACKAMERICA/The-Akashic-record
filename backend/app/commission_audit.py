from __future__ import annotations

from .control import audit_tail


def case_audit_events(case_id: str, workspace_id: str, limit: int = 200) -> list[dict]:
    events = audit_tail(max(1, min(limit * 5, 2000)), workspace_id=workspace_id, include_commission=True)
    out: list[dict] = []
    for event in events:
        if not str(event.get("action") or "").startswith("commission."):
            continue
        payload = event.get("payload") or {}
        if event.get("object_id") == case_id or payload.get("case_id") == case_id:
            out.append(event)
            if len(out) >= limit:
                break
    return out
