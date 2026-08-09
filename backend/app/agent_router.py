from __future__ import annotations

from dataclasses import dataclass

from .media import generate_image, generate_video
from .orchestrator import answer
from .tools import run_python


@dataclass
class TaskResult:
    kind: str
    output: dict


async def execute_task(kind: str, prompt: str, options: dict | None = None, workspace_id: str = "default") -> TaskResult:
    options = options or {}
    kind = (kind or "research").lower()
    if kind in {"research", "answer", "text"}:
        return TaskResult(kind="text", output=await answer(prompt, research=bool(options.get("research", True)), workspace_id=workspace_id))
    if kind in {"code", "python"}:
        result = run_python(prompt, timeout=int(options.get("timeout", 10)))
        return TaskResult(kind="code", output=result)
    if kind == "image":
        artifact = await generate_image(prompt, size=str(options.get("size", "1024x1024")), workspace_id=workspace_id)
        return TaskResult(kind="artifact", output=artifact)
    if kind == "video":
        artifact = await generate_video(prompt, seconds=int(options.get("seconds", 8)), workspace_id=workspace_id)
        return TaskResult(kind="artifact", output=artifact)
    raise ValueError(f"Unsupported task kind: {kind}")
