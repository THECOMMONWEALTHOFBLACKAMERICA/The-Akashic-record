from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .control import audit
from .ipfs import IPFSError, IPFSPublicationDisabled, status as ipfs_status
from .publications import list_publications, publish_artifact
from .security import require_admin

router = APIRouter(prefix="/v1/admin/publications", tags=["publications"])


class PublishRequest(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=64)
    workspace_id: str = Field(min_length=1, max_length=64)
    acknowledge_public_immutable_storage: bool = False


@router.get("/ipfs/status")
def publication_status(admin: dict = Depends(require_admin)):
    return ipfs_status()


@router.post("/ipfs")
def publish(req: PublishRequest, admin: dict = Depends(require_admin)):
    if not req.acknowledge_public_immutable_storage:
        raise HTTPException(
            status_code=400,
            detail="Publication requires acknowledge_public_immutable_storage=true because IPFS content may become public and difficult to retract.",
        )
    try:
        result = publish_artifact(req.artifact_id, req.workspace_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Artifact not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (IPFSPublicationDisabled, IPFSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit(
        "artifact.published_ipfs",
        "artifact",
        req.artifact_id,
        {
            "artifact_cid": result["artifact_cid"],
            "manifest_cid": result["manifest_cid"],
            "deduplicated": result.get("deduplicated", False),
        },
        workspace_id=req.workspace_id,
        actor=admin["label"],
    )
    return result


@router.get("/ipfs/{workspace_id}")
def publications(workspace_id: str, limit: int = 100, admin: dict = Depends(require_admin)):
    return {"publications": list_publications(workspace_id, max(1, min(limit, 500)))}
