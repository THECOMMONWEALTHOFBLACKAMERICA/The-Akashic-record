from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .memory import recall, remember, stats
from .orchestrator import answer
from .settings import settings
from .sources import search_all

app = FastAPI(title="T.A.R. API", version="0.2.0")
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "tar-api", "version": "0.2.0", "memory": stats()}


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
    return {"query": req.query, "results": recall(req.query, req.limit)}


@app.get("/v1/memory/stats")
def memory_stats():
    return stats()
