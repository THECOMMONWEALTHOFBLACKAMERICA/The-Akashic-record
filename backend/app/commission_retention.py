from __future__ import annotations

from .artifacts import delete_artifact
from .commission import delete_case, export_case
from .commission_access import list_case_access, revoke_case_access
from .control import audit


def _artifact_ids(evidence: list[dict]) -> set[str]:
    ids: set[str] = set()
    for item in evidence:
        metadata = item.get("retrieval_metadata") or {}
        original_id = metadata.get("original_artifact_id")
        if isinstance(original_id, str) and original_id:
            ids.add(original_id)
        for derived in item.get("derived_artifacts") or []:
            if isinstance(derived, str) and derived:
                ids.add(derived)
            elif isinstance(derived, dict):
                artifact_id = derived.get("artifact_id")
                if isinstance(artifact_id, str) and artifact_id:
                    ids.add(artifact_id)
    return ids


def delete_case_with_retention(case_id: str, workspace_id: str, *, actor: str, policy_basis: str) -> dict:
    exported = export_case(case_id, workspace_id)
    artifact_ids = _artifact_ids(exported.get("evidence") or [])
    access_rows = list_case_access(case_id, workspace_id)

    result = delete_case(case_id, workspace_id, actor=actor, policy_basis=policy_basis)

    deleted_artifacts: list[str] = []
    artifact_failures: list[dict] = []
    for artifact_id in sorted(artifact_ids):
        try:
            if delete_artifact(artifact_id, workspace_id):
                deleted_artifacts.append(artifact_id)
        except Exception as exc:
            artifact_failures.append({"artifact_id": artifact_id, "error": str(exc)})

    revoked_keys: list[str] = []
    for access in access_rows:
        key_id = access.get("key_id")
        if key_id and revoke_case_access(case_id, workspace_id, key_id):
            revoked_keys.append(key_id)

    cleanup = {
        **result,
        "artifact_records_targeted": len(artifact_ids),
        "artifacts_deleted": deleted_artifacts,
        "artifact_deletion_failures": artifact_failures,
        "access_grants_revoked": len(revoked_keys),
        "complete": not artifact_failures,
    }
    audit(
        "commission.retention_cleanup",
        "commission_case",
        case_id,
        {
            "case_id": case_id,
            "policy_basis": policy_basis,
            "artifact_records_targeted": len(artifact_ids),
            "artifacts_deleted": len(deleted_artifacts),
            "artifact_deletion_failures": artifact_failures,
            "access_grants_revoked": len(revoked_keys),
            "complete": cleanup["complete"],
        },
        workspace_id=workspace_id,
        actor=actor,
    )
    return cleanup
