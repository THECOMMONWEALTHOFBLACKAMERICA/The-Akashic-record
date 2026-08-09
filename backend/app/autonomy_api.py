from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_identity
from .autonomy import get_run, run_goal
from .control import audit

router = APIRouter(prefix="/v1/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20_000)


@router.post("/run")
async def execute_agent(req: AgentRunRequest, identity: dict = Depends(require_identity)):
    workspace_id = identity["workspace_id"]
    try:
        result = await run_goal(req.goal, workspace_id)
        audit(
            "agent.completed",
            "agent_run",
            result["run_id"],
            {"steps": len(result.get("steps", []))},
            workspace_id=workspace_id,
            actor=identity["label"],
        )
        return result
    except Exception as exc:
        audit(
            "agent.failed",
            "agent_run",
            "",
            {"error": str(exc)[:1000]},
            workspace_id=workspace_id,
            actor=identity["label"],
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
def agent_run(run_id: str, identity: dict = Depends(require_identity)):
    result = get_run(run_id, identity["workspace_id"])
    if not result:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return result
