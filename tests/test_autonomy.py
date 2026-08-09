import asyncio
import uuid

from backend.app import autonomy


def test_autonomy_plan_never_includes_unlisted_tools(monkeypatch):
    monkeypatch.setenv("TAR_AUTONOMY_TOOLS", "search,recall,research,pdf")
    monkeypatch.setenv("TAR_AUTONOMY_MAX_STEPS", "3")
    plan = asyncio.run(autonomy.plan_goal("Research this topic and produce a PDF report"))
    assert 1 <= len(plan) <= 3
    assert {step["tool"] for step in plan} <= {"search", "recall", "research", "pdf"}
    assert "code" not in {step["tool"] for step in plan}


def test_autonomy_recall_only_run_is_workspace_scoped(monkeypatch):
    workspace = "agent-" + uuid.uuid4().hex
    monkeypatch.setenv("TAR_AUTONOMY_TOOLS", "recall")
    monkeypatch.setenv("TAR_AUTONOMY_MAX_STEPS", "2")
    result = asyncio.run(autonomy.run_goal("find remembered evidence", workspace))
    assert result["status"] == "completed"
    assert result["workspace_id"] == workspace
    assert len(result["steps"]) == 1
    saved = autonomy.get_run(result["run_id"], workspace)
    assert saved is not None
    assert saved["status"] == "completed"
    assert autonomy.get_run(result["run_id"], "other-workspace") is None
