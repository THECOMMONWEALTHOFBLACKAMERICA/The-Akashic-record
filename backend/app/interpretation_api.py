from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_identity
from .control import audit
from .interpretation import (
    PRINCIPLES,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    build_training_example,
    evaluate_case,
    get_case,
    list_cases,
    save_case,
)

router = APIRouter(prefix="/v1/interpretation", tags=["interpretation"])


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid4()), max_length=64)
    kind: str = Field(default="unknown", max_length=80)
    stance: Literal["supports", "contradicts", "context"] = "supports"
    summary: str = Field(min_length=1, max_length=20_000)
    source_ref: str = Field(default="", max_length=3_000)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class InfluenceAssessment(BaseModel):
    ai_role: Literal["created", "amplified", "scaffolded", "unknown"] = "unknown"
    pre_ai_baseline: bool = False
    note: str = Field(default="", max_length=5_000)


class ClaimInput(BaseModel):
    claim_id: str = Field(default_factory=lambda: str(uuid4()), max_length=64)
    statement: str = Field(min_length=1, max_length=20_000)
    layer: Literal["observation", "interpretation"] = "interpretation"
    domain: str = Field(default="general", max_length=100)
    declared_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=200)
    human_corrections: list[str] = Field(default_factory=list, max_length=100)
    contradictions: list[str] = Field(default_factory=list, max_length=100)
    influence: InfluenceAssessment = Field(default_factory=InfluenceAssessment)


class AgencySignals(BaseModel):
    human_goal_origin: bool = False
    human_final_decision: bool = False
    can_explain_without_ai: bool = False
    can_detect_ai_error: bool = False
    skill_transferred: bool = False
    ai_originated_goal: bool = False
    cannot_proceed_without_ai: bool = False
    accepted_without_verification: bool = False


class InterpretationCaseInput(BaseModel):
    case_id: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=1_000)
    subject_ref: str = Field(default="anonymous", max_length=200)
    claims: list[ClaimInput] = Field(default_factory=list, max_length=500)
    agency: AgencySignals = Field(default_factory=AgencySignals)


@router.get("/principles")
def principles(identity: dict = Depends(require_identity)):
    return {"protocol": PROTOCOL_NAME, "version": PROTOCOL_VERSION, "principles": list(PRINCIPLES)}


@router.post("/evaluate")
def evaluate(req: InterpretationCaseInput, identity: dict = Depends(require_identity)):
    payload = req.model_dump(mode="json")
    result = evaluate_case(payload)
    audit(
        "interpretation.evaluated",
        "interpretation_case",
        req.case_id or "",
        {"claims": len(req.claims), "revision_required": result["summary"]["revision_required"]},
        workspace_id=identity["workspace_id"],
        actor=identity["label"],
    )
    return result


@router.post("/training-example")
def training_example(req: InterpretationCaseInput, identity: dict = Depends(require_identity)):
    payload = req.model_dump(mode="json")
    evaluation = evaluate_case(payload)
    return build_training_example(payload, evaluation)


@router.post("/cases")
def create_or_update_case(req: InterpretationCaseInput, identity: dict = Depends(require_identity)):
    payload = req.model_dump(mode="json")
    evaluation = evaluate_case(payload)
    try:
        stored = save_case(payload, evaluation, workspace_id=identity["workspace_id"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit(
        "interpretation.saved",
        "interpretation_case",
        stored["case_id"],
        {"claims": len(req.claims), "subject_ref": req.subject_ref},
        workspace_id=identity["workspace_id"],
        actor=identity["label"],
    )
    return {"record": stored, "evaluation": evaluation}


@router.get("/cases")
def cases(limit: int = 100, identity: dict = Depends(require_identity)):
    return {"cases": list_cases(limit, workspace_id=identity["workspace_id"])}


@router.get("/cases/{case_id}")
def case(case_id: str, identity: dict = Depends(require_identity)):
    found = get_case(case_id, workspace_id=identity["workspace_id"])
    if not found:
        raise HTTPException(status_code=404, detail="Interpretation case not found")
    return found
