import re
import httpx

from .memory import recall, remember
from .settings import settings
from .sources import search_all

_TAGS = re.compile(r"<[^>]+>")


def clean(text: str) -> str:
    return _TAGS.sub("", text or "").replace("&quot;", '"').replace("&#039;", "'")


async def call_model(prompt: str) -> str:
    if settings.llm_provider == "echo" or not settings.llm_base_url:
        return "Development mode: connect a supported LLM endpoint to generate synthesized answers. Retrieved evidence and memory are returned separately."
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are T.A.R. Distinguish sourced facts from inference, cite supplied evidence numbers, prefer primary sources, and say when evidence is insufficient."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(settings.llm_base_url.rstrip("/") + "/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def answer(query: str, research: bool = True):
    memory_hits = recall(query, limit=5)
    live_evidence = await search_all(query, limit=4) if research else []
    if live_evidence:
        remember(live_evidence)

    evidence = []
    seen = set()
    for item in memory_hits + live_evidence:
        key = (item.get("source"), item.get("url"), item.get("title"))
        if key not in seen:
            seen.add(key)
            evidence.append(item)

    context = "\n".join(
        f"[{i + 1}] {x['source']} | {x['title']} | {x.get('url', '')} | {clean(x.get('snippet', ''))}"
        for i, x in enumerate(evidence[:12])
    )
    prompt = f"Question: {query}\n\nEvidence:\n{context}\n\nAnswer using the evidence where relevant. Do not invent citations. Separate verified facts from interpretation."
    response = await call_model(prompt)
    return {
        "query": query,
        "answer": response,
        "sources": evidence[:12],
        "memory_hits": len(memory_hits),
        "live_hits": len(live_evidence),
        "research": research,
    }
