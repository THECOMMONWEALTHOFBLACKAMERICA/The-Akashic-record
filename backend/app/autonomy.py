from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .bootstrap import schema_bootstrap_enabled
from .document_tools import create_docx, create_pdf
from .media import generate_image, generate_video
from .memory import Base, engine
from .orchestrator import answer, call_model
from .retrieval import hybrid_recall
from .sources import search_all


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), index=True)
    plan_json: Mapped[str] = mapped_column(Text, default="[]")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentStepRecord(Base):
    __tablename__ = "agent_steps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    tool: Mapped[str] = mapped_column(String(50))
    instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), index=True)
    output_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


if schema_bootstrap_enabled():
    Base.metadata.create_all(engine)


DEFAULT_TOOLS = {"search", "recall", "research", "pdf", "docx", "image", "video"}
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _tool_allowlist() -> set[str]:
    configured = os.getenv("TAR_AUTONOMY_TOOLS", "").strip()
    if not configured:
        return set(DEFAULT_TOOLS)
    requested = {x.strip().lower() for x in configured.split(",") if x.strip()}
    return DEFAULT_TOOLS & requested


def _max_steps() -> int:
    try:
        return max(1, min(int(os.getenv("TAR_AUTONOMY_MAX_STEPS", "6")), 10))
    except ValueError:
        return 6


def _fallback_plan(goal: str, allowed: set[str]) -> list[dict]:
    plan: list[dict] = []
    lower = goal.lower()
    if "search" in allowed:
        plan.append({"tool": "search", "instruction": goal})
    if "research" in allowed:
        plan.append({"tool": "research", "instruction": goal})
    if any(word in lower for word in ("pdf", "report")) and "pdf" in allowed:
        plan.append({"tool": "pdf", "instruction": "Create a cited research report from the accumulated result."})
    elif any(word in lower for word in ("docx", "word document", "document")) and "docx" in allowed:
        plan.append({"tool": "docx", "instruction": "Create a document from the accumulated result."})
    return plan[: _max_steps()] or [{"tool": "recall", "instruction": goal}]


async def plan_goal(goal: str) -> list[dict]:
    allowed = _tool_allowlist()
    if not allowed:
        raise RuntimeError("No autonomous tools are enabled")

    planner_prompt = f"""Create a minimal execution plan for this goal: {goal}
Allowed tools: {', '.join(sorted(allowed))}.
Return JSON only in this exact shape: {{"steps":[{{"tool":"search","instruction":"..."}}]}}.
Use no more than {_max_steps()} steps. Never invent tools. Prefer research/search/recall before artifact generation. Do not include code execution, shell access, credential operations, destructive actions, purchases, external messaging, or governance changes."""
    try:
        raw = await call_model(planner_prompt)
        match = _JSON_RE.search(raw)
        if match:
            payload = json.loads(match.group(0))
            steps = []
            for item in payload.get("steps", []):
                tool = str(item.get("tool", "")).lower().strip()
                instruction = str(item.get("instruction", "")).strip()[:10_000]
                if tool in allowed and instruction:
                    steps.append({"tool": tool, "instruction": instruction})
                if len(steps) >= _max_steps():
                    break
            if steps:
                return steps
    except Exception:
        pass
    return _fallback_plan(goal, allowed)


def _compact_context(outputs: list[dict], max_chars: int = 20_000) -> str:
    parts: list[str] = []
    for item in outputs[-5:]:
        try:
            parts.append(json.dumps(item, ensure_ascii=False, default=str))
        except Exception:
            parts.append(str(item))
    return "\n".join(parts)[-max_chars:]


async def _execute_step(tool: str, instruction: str, goal: str, workspace_id: str, outputs: list[dict]) -> dict:
    context = _compact_context(outputs)
    if tool == "search":
        results = await search_all(instruction or goal, limit=6)
        return {"tool": tool, "query": instruction or goal, "results": results[:24]}
    if tool == "recall":
        results = hybrid_recall(instruction or goal, limit=12, workspace_id=workspace_id)
        return {"tool": tool, "query": instruction or goal, "results": results}
    if tool == "research":
        query = instruction or goal
        if context:
            query += f"\n\nPrior step context:\n{context}"
        result = await answer(query, research=True, workspace_id=workspace_id)
        return {"tool": tool, "result": result}
    if tool in {"pdf", "docx"}:
        source_text = ""
        for item in reversed(outputs):
            answer_text = item.get("result", {}).get("answer") if isinstance(item.get("result"), dict) else None
            if answer_text:
                source_text = str(answer_text)
                break
        if not source_text:
            source_text = context or goal
        title = goal.strip().replace("\n", " ")[:100] or "T.A.R. Report"
        artifact = create_pdf(title, source_text, workspace_id) if tool == "pdf" else create_docx(title, source_text, workspace_id)
        return {"tool": tool, "artifact": artifact}
    if tool == "image":
        artifact = await generate_image(instruction or goal, workspace_id=workspace_id)
        return {"tool": tool, "artifact": artifact}
    if tool == "video":
        artifact = await generate_video(instruction or goal, workspace_id=workspace_id)
        return {"tool": tool, "artifact": artifact}
    raise ValueError(f"Tool is not allowed: {tool}")


async def run_goal(goal: str, workspace_id: str = "default") -> dict:
    run_id = uuid.uuid4().hex
    plan = await plan_goal(goal)
    with Session(engine) as session:
        session.add(AgentRunRecord(run_id=run_id, workspace_id=workspace_id, goal=goal, status="running", plan_json=json.dumps(plan, ensure_ascii=False)))
        session.commit()

    outputs: list[dict] = []
    try:
        for ordinal, step in enumerate(plan, start=1):
            tool = step["tool"]
            instruction = step["instruction"]
            with Session(engine) as session:
                row = AgentStepRecord(run_id=run_id, workspace_id=workspace_id, ordinal=ordinal, tool=tool, instruction=instruction, status="running")
                session.add(row)
                session.commit()
                step_id = row.id
            try:
                output = await _execute_step(tool, instruction, goal, workspace_id, outputs)
                outputs.append(output)
                with Session(engine) as session:
                    row = session.get(AgentStepRecord, step_id)
                    row.status = "completed"
                    row.output_json = json.dumps(output, ensure_ascii=False, default=str)[:200_000]
                    row.finished_at = datetime.now(timezone.utc)
                    session.commit()
            except Exception as exc:
                with Session(engine) as session:
                    row = session.get(AgentStepRecord, step_id)
                    row.status = "failed"
                    row.error = str(exc)[:20_000]
                    row.finished_at = datetime.now(timezone.utc)
                    session.commit()
                raise

        result = {"run_id": run_id, "goal": goal, "status": "completed", "plan": plan, "steps": outputs, "workspace_id": workspace_id}
        with Session(engine) as session:
            row = session.get(AgentRunRecord, run_id)
            row.status = "completed"
            row.result_json = json.dumps(result, ensure_ascii=False, default=str)[:500_000]
            row.finished_at = datetime.now(timezone.utc)
            session.commit()
        return result
    except Exception as exc:
        with Session(engine) as session:
            row = session.get(AgentRunRecord, run_id)
            row.status = "failed"
            row.error = str(exc)[:20_000]
            row.finished_at = datetime.now(timezone.utc)
            session.commit()
        raise


def get_run(run_id: str, workspace_id: str) -> dict | None:
    with Session(engine) as session:
        run = session.scalar(select(AgentRunRecord).where(AgentRunRecord.run_id == run_id, AgentRunRecord.workspace_id == workspace_id))
        if not run:
            return None
        steps = session.scalars(select(AgentStepRecord).where(AgentStepRecord.run_id == run_id, AgentStepRecord.workspace_id == workspace_id).order_by(AgentStepRecord.ordinal.asc())).all()
        return {
            "run_id": run.run_id,
            "goal": run.goal,
            "status": run.status,
            "plan": json.loads(run.plan_json or "[]"),
            "result": json.loads(run.result_json) if run.result_json else None,
            "error": run.error,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "steps": [
                {
                    "ordinal": row.ordinal,
                    "tool": row.tool,
                    "instruction": row.instruction,
                    "status": row.status,
                    "output": json.loads(row.output_json) if row.output_json else None,
                    "error": row.error,
                }
                for row in steps
            ],
        }
