from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .artifacts import save_artifact
from .auth import require_authenticated_identity
from .commission import add_evidence, create_case, export_case, list_cases, list_evidence, review_evidence, update_case
from .commission_access import accessible_case_ids, grant_case_access, has_case_access, list_case_access, revoke_case_access
from .commission_research import research_case
from .commission_retention import delete_case_with_retention
from .control import audit

router = APIRouter(prefix="/v1/commission", tags=["commission"])


class CaseCreate(BaseModel):
    application_ref: str = Field(default="", max_length=200)
    applicant_label: str = Field(default="", max_length=500)


class CaseUpdate(BaseModel):
    status: str | None = None
    restricted_research: bool | None = None
    legal_hold: bool | None = None
    retention_policy: str | None = Field(default=None, max_length=200)


class CaseResearch(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    include_dawes: bool = False
    broaden_web: bool = False
    persist_as_evidence: bool = True
    limit: int = Field(default=5, ge=1, le=25)


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


class AccessGrant(BaseModel):
    key_id: str = Field(min_length=1, max_length=64)
    role: str = Field(default="readonly", max_length=40)


def _require(case_id: str, identity: dict, *, write: bool = False, review: bool = False, manage: bool = False) -> None:
    if not has_case_access(case_id, identity["workspace_id"], identity["key_id"], write=write, review=review, manage=manage):
        raise HTTPException(status_code=403, detail="Commission case access denied")


@router.post("/cases")
def new_case(req: CaseCreate, identity: dict = Depends(require_authenticated_identity)):
    result = create_case(identity["workspace_id"], req.application_ref, req.applicant_label, identity["label"])
    grant_case_access(result["case_id"], identity["workspace_id"], identity["key_id"], "owner")
    return result


@router.get("/cases")
def cases(limit: int = 200, identity: dict = Depends(require_authenticated_identity)):
    allowed = accessible_case_ids(identity["workspace_id"], identity["key_id"])
    rows = [r for r in list_cases(identity["workspace_id"], max(1, min(limit, 500))) if r["case_id"] in allowed]
    return {"cases": rows}


@router.patch("/cases/{case_id}")
def patch_case(case_id: str, req: CaseUpdate, identity: dict = Depends(require_authenticated_identity)):
    # Legal holds, retention and case dispositions are policy-bearing controls.
    if req.legal_hold is not None or req.retention_policy is not None or req.status in {"approved", "denied", "appealed", "closed"}:
        _require(case_id, identity, manage=True)
    else:
        _require(case_id, identity, write=True)
    try:
        return update_case(case_id, identity["workspace_id"], status=req.status, restricted_research=req.restricted_research, legal_hold=req.legal_hold, retention_policy=req.retention_policy, actor=identity["label"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, ValueError) else 404, detail=str(exc)) from exc


@router.post("/cases/{case_id}/research")
async def case_research(case_id: str, req: CaseResearch, identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity, write=True)
    try:
        return await research_case(case_id, identity["workspace_id"], req.query, include_dawes=req.include_dawes, broaden_web=req.broaden_web, persist_as_evidence=req.persist_as_evidence, actor=identity["label"], limit=req.limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/cases/{case_id}/export")
def case_export(case_id: str, identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity)
    try:
        return export_case(case_id, identity["workspace_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/cases/{case_id}")
def remove_case(case_id: str, req: CaseDelete, identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity, manage=True)
    try:
        return delete_case_with_retention(case_id, identity["workspace_id"], actor=identity["label"], policy_basis=req.policy_basis)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/cases/{case_id}/access")
def grant_access(case_id: str, req: AccessGrant, identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity, manage=True)
    try:
        result = grant_case_access(case_id, identity["workspace_id"], req.key_id, req.role)
        audit("commission.access_granted", "commission_case", case_id, {"key_id": req.key_id, "role": req.role}, workspace_id=identity["workspace_id"], actor=identity["label"])
        return result
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cases/{case_id}/access")
def access_list(case_id: str, identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity, manage=True)
    return {"access": list_case_access(case_id, identity["workspace_id"])}


@router.delete("/cases/{case_id}/access/{key_id}")
def revoke_access(case_id: str, key_id: str, identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity, manage=True)
    if key_id == identity["key_id"]:
        raise HTTPException(status_code=400, detail="Grant another owner/commissioner credential before revoking your own access")
    removed = revoke_case_access(case_id, identity["workspace_id"], key_id)
    if removed:
        audit("commission.access_revoked", "commission_case", case_id, {"key_id": key_id}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return {"revoked": removed}


@router.post("/cases/{case_id}/evidence")
def new_evidence(case_id: str, req: EvidenceCreate, identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity, write=True)
    try:
        return add_evidence(case_id, identity["workspace_id"], title=req.title, source_tier=req.source_tier, source=req.source, source_uri=req.source_uri, citation=req.citation, retrieval_metadata=req.retrieval_metadata, original_filename=req.original_filename, original_sha256=req.original_sha256, uploader=req.uploader or identity["label"], claimed_provenance=req.claimed_provenance, media_type=req.media_type, transformations=req.transformations, derived_artifacts=req.derived_artifacts, actor=identity["label"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cases/{case_id}/evidence/upload")
async def upload_evidence(case_id: str, file: UploadFile = File(...), title: str = Form(default=""), source_tier: int = Form(default=1), source: str = Form(default="applicant_submission"), claimed_provenance: str = Form(default=""), citation: str = Form(default=""), identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity, write=True)
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB Commission upload limit")
    try:
        original = save_artifact(file.filename or "evidence.bin", data, file.content_type or "application/octet-stream", {"classification": "commission_original_evidence", "case_id": case_id, "public_ipfs_allowed": False}, identity["workspace_id"])
        return add_evidence(case_id, identity["workspace_id"], title=title or file.filename or "Submitted evidence", source_tier=source_tier, source=source, citation=citation, retrieval_metadata={"original_artifact_id": original["artifact_id"], "storage_backend": original.get("storage_backend")}, original_filename=file.filename or "evidence.bin", original_bytes=data, uploader=identity["label"], claimed_provenance=claimed_provenance, media_type=file.content_type or "application/octet-stream", transformations=[], derived_artifacts=[], actor=identity["label"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cases/{case_id}/evidence")
def evidence(case_id: str, identity: dict = Depends(require_authenticated_identity)):
    _require(case_id, identity)
    try:
        return {"evidence": list_evidence(case_id, identity["workspace_id"])}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/evidence/{evidence_id}/review")
def review(evidence_id: str, req: EvidenceReview, identity: dict = Depends(require_authenticated_identity)):
    allowed = accessible_case_ids(identity["workspace_id"], identity["key_id"])
    matching_case = None
    for case_id in allowed:
        if any(e["evidence_id"] == evidence_id for e in list_evidence(case_id, identity["workspace_id"])):
            matching_case = case_id
            break
    if not matching_case or not has_case_access(matching_case, identity["workspace_id"], identity["key_id"], review=True):
        raise HTTPException(status_code=403, detail="Commission reviewer access required")
    try:
        return review_evidence(evidence_id, identity["workspace_id"], status=req.status, reviewer=identity["label"], review_notes=req.review_notes, exclusion_reason=req.exclusion_reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
