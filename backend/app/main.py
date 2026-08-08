from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .ingestion import get_job, ingest_bytes, list_documents
from .memory import remember, stats
from .orchestrator import answer
from .retrieval import hybrid_recall
from .settings import settings
from .sources import search_all

app = FastAPI(title="T.A.R. API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/health")
def health():
    return {"status": "ok", "service": "tar-api", "version": "0.3.0", "memory": stats()}


@app.post("/v1/ask")
async def ask(req: AskRequest):
    try:
        return await answer(req.query, research=req.research)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/v1/search")
async def search(req: SearchRequest):
    results = await search_all(req.query, req.sources, req.limit)
    stored = remember(results) if req.persist else 0
    return {"query": req.query, "results": results, "stored": stored}


@app.post("/v1/memory/recall")
def memory_recall(req: RecallRequest):
    return {"query": req.query, "results": hybrid_recall(req.query, req.limit, source=req.source)}


@app.get("/v1/memory/stats")
def memory_stats():
    return stats()


@app.post("/v1/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    source: str = Form(default="upload"),
    source_uri: str = Form(default=""),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB ingestion limit")
    try:
        return ingest_bytes(file.filename or "upload.txt", data, title=title, source=source, source_uri=source_uri)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/ingest/jobs/{job_id}")
def ingest_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/v1/documents")
def documents(limit: int = 100):
    return {"documents": list_documents(max(1, min(limit, 500)))}
