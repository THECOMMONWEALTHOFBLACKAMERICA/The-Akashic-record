from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_identity
from .commission import add_evidence, create_case, delete_case, export_case, list_cases, list_evidence, review_evidence, update_case

router = APIRouter(prefix="/v1/commission", tags=["commission"])


class CaseCreate(BaseModel):
    application_ref: str = Field(default="", max_length=200)
    applicant_label: str = Field(default="", max_length=500)


class CaseUpdate(BaseModel):
    status: str | None = None
    restricted_research: bool | None = None
    legal_hold: bool | None = None
    retention_policy: str | None = Field(default=None, max_length=200)


class EvidenceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    source_tier: int = Field(ge=1, le=3)
    source: str = Field(default="", max_length=300)
    source_uri: str = Field(default="", max_length=3000)
    citation: str = ""
    retrieval_metadata: dict = Field(default_factory=dict)
    original_filename: str = Field(default="", max_length=1000)
    original_sha256: str = Field(default="", max_length=64)
    uploader: str = Field(default="", max_length=500)
    claimed_provenance: str = ""
    media_type: str = Field(default="application/octet-stream", max_length=200)
    transformations: list = Field(default_factory=list)
    derived_artifacts: list = Field(default_factory=list)


class EvidenceReview(BaseModel):
    status: str
    review_notes: str = ""
    exclusion_reason: str = ""


class CaseDelete(BaseModel):
    policy_basis: str = Field(min_length=1, max_length=2000)


@router.post("/cases")
def new_case(req: CaseCreate, identity: dict = Depends(require_identity)):
    return create_case(identity["workspace_id"], req.application_ref, req.applicant_label, identity["label"])


@router.get("/cases")
def cases(limit: int = 200, identity: dict = Depends(require_identity)):
    return {"cases": list_cases(identity["workspace_id"], max(1, min(limit, 500)))}


@router.patch("/cases/{case_id}")
def patch_case(case_id: str, req: CaseUpdate, identity: dict = Depends(require_identity)):
    try:
        return update_case(case_id, identity["workspace_id"], status=req.status, restricted_research=req.restricted_research, legal_hold=req.legal_hold, retention_policy=req.retention_policy, actor=identity["label"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, ValueError) else 404, detail=str(exc)) from exc


@router.get("/cases/{case_id}/export")
def case_export(case_id: str, identity: dict = Depends(require_identity)):
    try:
        return export_case(case_id, identity["workspace_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/cases/{case_id}")
def remove_case(case_id: str, req: CaseDelete, identity: dict = Depends(require_identity)):
    try:
        return delete_case(case_id, identity["workspace_id"], actor=identity["label"], policy_basis=req.policy_basis)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/cases/{case_id}/evidence")
def new_evidence(case_id: str, req: EvidenceCreate, identity: dict = Depends(require_identity)):
    try:
        return add_evidence(case_id, identity["workspace_id"], title=req.title, source_tier=req.source_tier, source=req.source, source_uri=req.source_uri, citation=req.citation, retrieval_metadata=req.retrieval_metadata, original_filename=req.original_filename, original_sha256=req.original_sha256, uploader=req.uploader or identity["label"], claimed_provenance=req.claimed_provenance, media_type=req.media_type, transformations=req.transformations, derived_artifacts=req.derived_artifacts, actor=identity["label"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cases/{case_id}/evidence")
def evidence(case_id: str, identity: dict = Depends(require_identity)):
    try:
        return {"evidence": list_evidence(case_id, identity["workspace_id"])}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/evidence/{evidence_id}/review")
def review(evidence_id: str, req: EvidenceReview, identity: dict = Depends(require_identity)):
    try:
        return review_evidence(evidence_id, identity["workspace_id"], status=req.status, reviewer=identity["label"], review_notes=req.review_notes, exclusion_reason=req.exclusion_reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
