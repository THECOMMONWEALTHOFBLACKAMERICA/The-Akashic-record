from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from .artifacts import artifact_metadata, get_artifact, is_protected_artifact
from .auth import require_authenticated_identity
from .commission_access import has_case_access

router = APIRouter(prefix="/v1/commission", tags=["commission"])


@router.get("/cases/{case_id}/artifacts/{artifact_id}")
def commission_artifact(case_id: str, artifact_id: str, identity: dict = Depends(require_authenticated_identity)):
    if not has_case_access(case_id, identity["workspace_id"], identity["key_id"]):
        raise HTTPException(status_code=403, detail="Commission case access denied")

    found = get_artifact(artifact_id, identity["workspace_id"], include_protected=True)
    if not found:
        raise HTTPException(status_code=404, detail="Artifact not found")
    row, data = found
    metadata = artifact_metadata(row)
    if not is_protected_artifact(row) or metadata.get("case_id") != case_id:
        raise HTTPException(status_code=404, detail="Commission case artifact not found")

    return Response(
        content=data,
        media_type=row.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{row.name}"',
            "X-TAR-SHA256": row.sha256,
            "Cache-Control": "private, no-store",
        },
    )
