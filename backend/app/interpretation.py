from __future__ import annotations

import json
from datetime import datetime, timezone
from math import prod
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .bootstrap import schema_bootstrap_enabled
from .memory import Base, engine

PROTOCOL_NAME = "T.A.R. Human Interpretation Protocol"
PROTOCOL_VERSION = "0.1.0"

PRINCIPLES: tuple[dict[str, str], ...] = (
    {"id":"revisable_model","name":"Keep a revisable model","rule":"Treat interpretations of a person as provisional and updateable, never as permanent identity facts."},
    {"id":"evidence_over_narrative","name":"Evidence outranks narrative","rule":"Primary records, direct corrections, and corroborated observations can overturn a coherent story."},
    {"id":"stage_not_seriousness","name":"Track project stage","rule":"Distinguish idea, active work, external validation, completion, and independent use instead of calling unfinished work fake."},
    {"id":"domain_contracts","name":"Separate evidentiary domains","rule":"Genealogy, engineering, fiction, philosophy, civic planning, and personal reflection require different evidentiary contracts."},
    {"id":"amplification_not_creation","name":"Distinguish amplification from creation","rule":"Do not claim AI created a trait when pre-AI evidence shows that trait already existed; use amplified, scaffolded, or unknown when appropriate."},
    {"id":"preserve_contradiction","name":"Preserve contradiction","rule":"Do not erase conflicting testimony merely to produce a cleaner personality theory."},
    {"id":"account_for_ai_influence","name":"Account for AI influence","rule":"A long-term AI partner is part of the subject's environment and should not pretend to be a neutral observer."},
    {"id":"increase_agency","name":"Increase human agency","rule":"Prefer assistance that improves human judgment and skill transfer over dependency on model outputs."},
    {"id":"corrections_are_data","name":"Corrections are high-value data","rule":"A person's correction of what they meant should trigger explicit model revision rather than defensive preservation of the old interpretation."},
    {"id":"confidence_is_not_evidence","name":"Confidence is not evidence","rule":"Fluent or confident language must never substitute for supporting evidence."},
)

EVIDENCE_WEIGHTS = {
    "primary_record":1.00, "direct_observation":0.90, "human_correction":0.90,
    "corroborated_testimony":0.85, "artifact":0.80, "direct_testimony":0.75,
    "self_report":0.65, "model_output":0.35, "narrative_inference":0.25, "unknown":0.20,
}

class InterpretationCaseRecord(Base):
    __tablename__ = "interpretation_cases"
    case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default")
    subject_ref: Mapped[str] = mapped_column(String(200), index=True, default="anonymous")
    title: Mapped[str] = mapped_column(String(1000))
    payload_json: Mapped[str] = mapped_column(Text)
    evaluation_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

if schema_bootstrap_enabled():
    InterpretationCaseRecord.__table__.create(engine, checkfirst=True)

def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))

def _evidence_strength(evidence: list[dict[str, Any]]) -> tuple[float, float, float]:
    buckets: dict[str, list[float]] = {"supports": [], "contradicts": [], "context": []}
    for item in evidence:
        kind = str(item.get("kind", "unknown")).strip().lower()
        term = _clamp(EVIDENCE_WEIGHTS.get(kind, EVIDENCE_WEIGHTS["unknown"]) * _clamp(item.get("confidence", 0.5)))
        stance = str(item.get("stance", "supports")).strip().lower()
        buckets[stance if stance in buckets else "supports"].append(term)
    def union(terms: list[float]) -> float:
        return 0.0 if not terms else _clamp(1.0 - prod(1.0 - term for term in terms))
    return union(buckets["supports"]), union(buckets["contradicts"]), union(buckets["context"])

def evaluate_agency(signals: dict[str, Any] | None) -> dict[str, Any]:
    signals = signals or {}
    positives = ("human_goal_origin","human_final_decision","can_explain_without_ai","can_detect_ai_error","skill_transferred")
    risks = ("ai_originated_goal","cannot_proceed_without_ai","accepted_without_verification")
    positive_count = sum(bool(signals.get(k, False)) for k in positives)
    risk_count = sum(bool(signals.get(k, False)) for k in risks)
    score = round(100.0 * (positive_count + (len(risks)-risk_count)) / (len(positives)+len(risks)), 1)
    band = "agency_expanding" if score >= 80 else "agency_preserved" if score >= 60 else "mixed" if score >= 40 else "dependency_concern"
    return {
        "score": score,
        "band": band,
        "strengths": [k for k in positives if bool(signals.get(k, False))],
        "concerns": [k for k in risks if bool(signals.get(k, False))],
        "note": "Heuristic workflow signal, not a psychological or clinical measurement.",
    }

def evaluate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    evidence = list(claim.get("evidence") or [])
    corrections = [str(x).strip() for x in (claim.get("human_corrections") or []) if str(x).strip()]
    contradictions = [str(x).strip() for x in (claim.get("contradictions") or []) if str(x).strip()]
    layer = str(claim.get("layer", "interpretation")).strip().lower()
    declared = _clamp(claim.get("declared_confidence", 0.5))
    support, contradict, context = _evidence_strength(evidence)
    influence = claim.get("influence") or {}
    ai_role = str(influence.get("ai_role", "unknown")).strip().lower()
    pre_ai_baseline = bool(influence.get("pre_ai_baseline", False))
    flags: list[str] = []
    if layer == "interpretation" and not evidence: flags.append("interpretation_without_evidence")
    if corrections: flags.append("human_correction_requires_revision")
    if contradictions or contradict > 0.0: flags.append("contradiction_must_be_preserved")
    if declared > support + 0.15: flags.append("confidence_exceeds_supporting_evidence")
    if ai_role == "created" and pre_ai_baseline: flags.append("ai_creation_claim_conflicts_with_pre_ai_baseline")

    if not evidence: status = "unsupported"
    elif corrections or contradictions or (contradict >= 0.35 and support >= 0.35): status = "contested"
    elif contradict > support and contradict >= 0.45: status = "contradicted"
    elif support >= 0.80 and contradict < 0.20: status = "well_supported"
    elif support >= 0.50: status = "supported"
    else: status = "tentative"

    recommended = round(min(declared, max(support - contradict * 0.5, 0.0)), 3)
    if status in {"contested","contradicted"}: recommended = min(recommended, 0.5)
    return {
        "claim_id": claim.get("claim_id", ""), "statement": claim.get("statement", ""),
        "layer": layer, "domain": claim.get("domain", "general"), "epistemic_status": status,
        "support_strength": round(support,3), "contradiction_strength": round(contradict,3), "context_strength": round(context,3),
        "declared_confidence": round(declared,3), "recommended_confidence": round(recommended,3),
        "revision_required": bool(corrections or contradictions or contradict >= 0.35 or "confidence_exceeds_supporting_evidence" in flags),
        "flags": flags, "preserved_human_corrections": corrections, "preserved_contradictions": contradictions,
        "ai_influence_assessment": {"ai_role": ai_role, "pre_ai_baseline": pre_ai_baseline, "causality_claim_allowed": not (ai_role == "created" and pre_ai_baseline)},
    }

def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    claims = [evaluate_claim(c) for c in (case.get("claims") or [])]
    return {
        "protocol": PROTOCOL_NAME, "protocol_version": PROTOCOL_VERSION,
        "case_title": case.get("title", ""), "subject_ref": case.get("subject_ref", "anonymous"),
        "summary": {
            "claims": len(claims),
            "supported_or_better": sum(c["epistemic_status"] in {"supported","well_supported"} for c in claims),
            "contested_or_contradicted": sum(c["epistemic_status"] in {"contested","contradicted"} for c in claims),
            "unsupported": sum(c["epistemic_status"] == "unsupported" for c in claims),
            "revision_required": sum(bool(c["revision_required"]) for c in claims),
            "mean_support_strength": round(sum(c["support_strength"] for c in claims)/len(claims),3) if claims else 0.0,
        },
        "agency": evaluate_agency(case.get("agency")),
        "claims": claims,
        "principles_applied": [p["id"] for p in PRINCIPLES],
    }

def build_training_example(case: dict[str, Any], evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    evaluation = evaluation or evaluate_case(case)
    return {
        "schema": "tar-human-interpretation-training-example/v1",
        "protocol_version": PROTOCOL_VERSION,
        "instruction": "Evaluate interpretations of a human as revisable claims. Separate observation from interpretation, prefer evidence over narrative coherence, preserve corrections and contradictions, avoid unsupported AI-causality claims, and assess whether AI assistance increases or replaces human agency.",
        "principles": list(PRINCIPLES), "input": case, "expected_checks": evaluation,
    }

def save_case(case: dict[str, Any], evaluation: dict[str, Any], workspace_id: str = "default") -> dict[str, Any]:
    case_id = str(case.get("case_id") or uuid4()); now = datetime.now(timezone.utc); payload = dict(case); payload["case_id"] = case_id
    with Session(engine) as session:
        record = session.get(InterpretationCaseRecord, case_id)
        if record and record.workspace_id != workspace_id: raise ValueError("Interpretation case not available in this workspace")
        if record:
            record.subject_ref = str(payload.get("subject_ref", record.subject_ref)); record.title = str(payload.get("title", record.title))
            record.payload_json = json.dumps(payload, ensure_ascii=False); record.evaluation_json = json.dumps(evaluation, ensure_ascii=False); record.updated_at = now
        else:
            record = InterpretationCaseRecord(case_id=case_id, workspace_id=workspace_id, subject_ref=str(payload.get("subject_ref","anonymous")), title=str(payload.get("title","Untitled interpretation case")), payload_json=json.dumps(payload,ensure_ascii=False), evaluation_json=json.dumps(evaluation,ensure_ascii=False), created_at=now, updated_at=now); session.add(record)
        session.commit(); session.refresh(record)
    return {"case_id":record.case_id,"workspace_id":record.workspace_id,"subject_ref":record.subject_ref,"title":record.title,"created_at":record.created_at.isoformat() if record.created_at else None,"updated_at":record.updated_at.isoformat() if record.updated_at else None}

def get_case(case_id: str, workspace_id: str = "default") -> dict[str, Any] | None:
    with Session(engine) as session:
        record = session.scalar(select(InterpretationCaseRecord).where(InterpretationCaseRecord.case_id == case_id, InterpretationCaseRecord.workspace_id == workspace_id))
        if not record: return None
        return {"case_id":record.case_id,"workspace_id":record.workspace_id,"subject_ref":record.subject_ref,"title":record.title,"case":json.loads(record.payload_json),"evaluation":json.loads(record.evaluation_json),"created_at":record.created_at.isoformat() if record.created_at else None,"updated_at":record.updated_at.isoformat() if record.updated_at else None}

def list_cases(limit: int = 100, workspace_id: str = "default") -> list[dict[str, Any]]:
    with Session(engine) as session:
        records = session.scalars(select(InterpretationCaseRecord).where(InterpretationCaseRecord.workspace_id == workspace_id).order_by(InterpretationCaseRecord.updated_at.desc()).limit(max(1,min(limit,500)))).all()
    return [{"case_id":r.case_id,"subject_ref":r.subject_ref,"title":r.title,"created_at":r.created_at.isoformat() if r.created_at else None,"updated_at":r.updated_at.isoformat() if r.updated_at else None} for r in records]
