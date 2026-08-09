from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_identity
from .control import audit
from .jobs import claim, complete, enqueue, fail, get_job
from .security import require_worker

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


class EnqueueRequest(BaseModel):
    kind: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=1, max_length=50_000)
    options: dict = Field(default_factory=dict)


class ClaimRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    capabilities: list[str] = Field(default_factory=list)
    lease_seconds: int = Field(default=120, ge=30, le=900)


class CompleteRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    result: dict


class FailRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    error: str = Field(min_length=1, max_length=20_000)
    retry: bool = True


@router.post("")
def create_job(req: EnqueueRequest, identity: dict = Depends(require_identity)):
    job = enqueue(req.kind, req.prompt, req.options, identity["workspace_id"])
    audit(
        "job.queued",
        "job",
        job["job_id"],
        {"kind": req.kind},
        workspace_id=identity["workspace_id"],
        actor=identity["label"],
    )
    return job


@router.get("/{job_id}")
def job_status(job_id: str, identity: dict = Depends(require_identity)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["workspace_id"] != identity["workspace_id"]:
        # Deliberately return 404 so a caller cannot enumerate another workspace's job IDs.
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/worker/claim")
def worker_claim(req: ClaimRequest, worker: dict = Depends(require_worker)):
    return claim(req.node_id, req.capabilities, req.lease_seconds) or {"job": None}


@router.post("/{job_id}/complete")
def worker_complete(job_id: str, req: CompleteRequest, worker: dict = Depends(require_worker)):
    try:
        result = complete(job_id, req.node_id, req.result)
        audit(
            "job.completed",
            "job",
            job_id,
            {"node_id": req.node_id},
            workspace_id=result["workspace_id"],
            actor=req.node_id,
        )
        return result
    except (KeyError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/fail")
def worker_fail(job_id: str, req: FailRequest, worker: dict = Depends(require_worker)):
    try:
        result = fail(job_id, req.node_id, req.error, req.retry)
        audit(
            "job.failed",
            "job",
            job_id,
            {"node_id": req.node_id, "retry": req.retry},
            workspace_id=result["workspace_id"],
            actor=req.node_id,
        )
        return result
    except (KeyError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
