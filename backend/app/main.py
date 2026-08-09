from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .agent_router import execute_task
from .artifacts import get_artifact, list_artifacts
from .auth import require_identity
from .control import audit, audit_tail, create_api_key, create_workspace, heartbeat_node, list_nodes, register_node, verify_audit_chain
from .document_api import router as document_router
from .governance import proposal as governance_proposal, status as governance_status
from .ingestion import get_job, ingest_bytes, list_documents
from .jobs_api import router as jobs_router
from .media_api import router as media_router
from .memory import remember, stats
from .orchestrator import answer
from .retrieval import hybrid_recall
from .security import require_admin
from .settings import settings
from .sources import search_all
from .tools import analyze_csv, image_metadata

app = FastAPI(title="T.A.R. API", version="0.10.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(jobs_router)
app.include_router(document_router)
app.include_router(media_router)


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20000)
    research: bool = True


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    sources: list[str] | None = None
    limit: int = Field(default=5, ge=1, le=25)
    persist: bool = True


class RecallRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=8, ge=1, le=50)
    source: str | None = None


class TaskRequest(BaseModel):
    kind: str = Field(default="research", max_length=50)
    prompt: str = Field(min_length=1, max_length=50000)
    options: dict = Field(default_factory=dict)


class WorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    owner: str = Field(default="local", max_length=500)


class KeyRequest(BaseModel):
    label: str = Field(min_length=1, max_length=500)
    workspace_id: str = Field(default="default", max_length=64)


class NodeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    endpoint: str = Field(default="", max_length=3000)
    capabilities: list[str] = Field(default_factory=list)


@app.get("/health")
def health():
    return {"status": "ok", "service": "tar-api", "version": "0.10.0", "memory": stats(), "governance": governance_status()}


@app.post("/v1/ask")
async def ask(req: AskRequest, identity: dict = Depends(require_identity)):
    try:
        result = await answer(req.query, research=req.research)
        audit("ask.completed", "query", "", {"research": req.research, "source_count": len(result.get("sources", []))}, workspace_id=identity["workspace_id"], actor=identity["label"])
        return result
    except Exception as exc:
        audit("ask.failed", "query", "", {"error": str(exc)}, workspace_id=identity["workspace_id"], actor=identity["label"])
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/v1/tasks")
async def tasks(req: TaskRequest, identity: dict = Depends(require_identity)):
    try:
        result = await execute_task(req.kind, req.prompt, req.options)
        object_id = str(result.output.get("artifact_id", "")) if isinstance(result.output, dict) else ""
        audit("task.completed", req.kind, object_id, {"kind": req.kind}, workspace_id=identity["workspace_id"], actor=identity["label"])
        return {"kind": result.kind, "output": result.output}
    except Exception as exc:
        audit("task.failed", req.kind, "", {"error": str(exc)}, workspace_id=identity["workspace_id"], actor=identity["label"])
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/search")
async def search(req: SearchRequest, identity: dict = Depends(require_identity)):
    results = await search_all(req.query, req.sources, req.limit)
    stored = remember(results) if req.persist else 0
    audit("search.completed", "search", "", {"sources": req.sources, "results": len(results), "stored": stored}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return {"query": req.query, "results": results, "stored": stored}


@app.post("/v1/memory/recall")
def memory_recall(req: RecallRequest, identity: dict = Depends(require_identity)):
    results = hybrid_recall(req.query, req.limit, source=req.source)
    audit("memory.recalled", "memory", "", {"results": len(results), "source": req.source}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return {"query": req.query, "results": results}


@app.get("/v1/memory/stats")
def memory_stats(identity: dict = Depends(require_identity)):
    return stats()


@app.post("/v1/ingest/file")
async def ingest_file(file: UploadFile = File(...), title: str | None = Form(default=None), source: str = Form(default="upload"), source_uri: str = Form(default=""), identity: dict = Depends(require_identity)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB ingestion limit")
    try:
        result = ingest_bytes(file.filename or "upload.txt", data, title=title, source=source, source_uri=source_uri, metadata={"workspace_id": identity["workspace_id"]})
        audit("document.ingested", "document", result.get("document_id", ""), {"filename": file.filename, "source": source, "chunks": result.get("chunks", 0)}, workspace_id=identity["workspace_id"], actor=identity["label"])
        return result
    except Exception as exc:
        audit("document.ingest_failed", "document", "", {"filename": file.filename, "error": str(exc)}, workspace_id=identity["workspace_id"], actor=identity["label"])
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/tools/csv")
async def csv_tool(file: UploadFile = File(...), identity: dict = Depends(require_identity)):
    data = await file.read()
    try:
        result = analyze_csv(data, file.filename or "data.csv")
        audit("tool.csv", "artifact", result["artifact"]["artifact_id"], {"filename": file.filename}, workspace_id=identity["workspace_id"], actor=identity["label"])
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/tools/image-metadata")
async def image_tool(file: UploadFile = File(...), identity: dict = Depends(require_identity)):
    data = await file.read()
    try:
        result = image_metadata(data, file.filename or "image")
        audit("tool.image_metadata", "artifact", result["artifact"]["artifact_id"], {"filename": file.filename}, workspace_id=identity["workspace_id"], actor=identity["label"])
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/ingest/jobs/{job_id}")
def ingest_job(job_id: str, identity: dict = Depends(require_identity)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/v1/documents")
def documents(limit: int = 100, identity: dict = Depends(require_identity)):
    return {"documents": list_documents(max(1, min(limit, 500)))}


@app.get("/v1/artifacts")
def artifacts(limit: int = 100, identity: dict = Depends(require_identity)):
    return {"artifacts": list_artifacts(max(1, min(limit, 500)))}


@app.get("/v1/artifacts/{artifact_id}")
def artifact(artifact_id: str, identity: dict = Depends(require_identity)):
    found = get_artifact(artifact_id)
    if not found:
        raise HTTPException(status_code=404, detail="Artifact not found")
    row, data = found
    headers = {"Content-Disposition": f'attachment; filename="{row.name}"', "X-TAR-SHA256": row.sha256}
    return Response(content=data, media_type=row.media_type, headers=headers)


@app.post("/v1/admin/workspaces")
def new_workspace(req: WorkspaceRequest, admin: dict = Depends(require_admin)):
    return create_workspace(req.name, req.owner)


@app.post("/v1/admin/api-keys")
def new_api_key(req: KeyRequest, admin: dict = Depends(require_admin)):
    try:
        return create_api_key(req.label, req.workspace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/audit")
def audit_log(limit: int = 100, identity: dict = Depends(require_identity)):
    return {"events": audit_tail(max(1, min(limit, 500)), workspace_id=identity["workspace_id"])}


@app.get("/v1/audit/verify")
def audit_verify(identity: dict = Depends(require_identity)):
    return verify_audit_chain(identity["workspace_id"])


@app.post("/v1/nodes")
def node_register(req: NodeRequest, admin: dict = Depends(require_admin)):
    return register_node(req.name, req.endpoint, req.capabilities)


@app.post("/v1/nodes/{node_id}/heartbeat")
def node_heartbeat(node_id: str, admin: dict = Depends(require_admin)):
    result = heartbeat_node(node_id)
    if not result:
        raise HTTPException(status_code=404, detail="Node not found")
    return result


@app.get("/v1/nodes")
def nodes(identity: dict = Depends(require_identity)):
    return {"nodes": list_nodes()}


@app.get("/v1/governance")
def governance(identity: dict = Depends(require_identity)):
    return governance_status()


@app.get("/v1/governance/proposals/{proposal_id}")
def governance_get_proposal(proposal_id: int, identity: dict = Depends(require_identity)):
    try:
        return governance_proposal(proposal_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
