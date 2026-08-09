from __future__ import annotations

import asyncio
import os
import re

import httpx

from .settings import settings

HEADERS = {"User-Agent": "TAR-Akashic-Records/1.0 research client; contact configured by operator"}
_TAGS = re.compile(r"<[^>]+>")


async def _json(url: str, params: dict, headers: dict | None = None):
    merged = {**HEADERS, **(headers or {})}
    async with httpx.AsyncClient(timeout=settings.request_timeout, headers=merged, follow_redirects=True) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def wikipedia(q: str, limit: int = 5):
    data = await _json("https://en.wikipedia.org/w/api.php", {"action": "query", "list": "search", "srsearch": q, "format": "json", "utf8": 1, "srlimit": limit})
    return [{"source": "wikipedia", "title": x["title"], "url": f"https://en.wikipedia.org/wiki/{x['title'].replace(' ', '_')}", "snippet": x.get("snippet", ""), "confidence": 0.55, "provenance": {"retrieved_via": "MediaWiki API"}} for x in data.get("query", {}).get("search", [])]


async def wikidata(q: str, limit: int = 5):
    data = await _json("https://www.wikidata.org/w/api.php", {"action": "wbsearchentities", "search": q, "language": "en", "format": "json", "limit": limit})
    return [{"source": "wikidata", "title": x.get("label", x["id"]), "url": f"https://www.wikidata.org/wiki/{x['id']}", "snippet": x.get("description", ""), "confidence": 0.65, "provenance": {"retrieved_via": "Wikidata API"}} for x in data.get("search", [])]


async def loc(q: str, limit: int = 5):
    data = await _json("https://www.loc.gov/search/", {"q": q, "fo": "json", "c": min(limit, 100), "at": "results,pagination"})
    out = []
    for x in data.get("results", [])[:limit]:
        description = x.get("description", "") or x.get("notes", "") or ""
        if isinstance(description, list):
            description = " ".join(str(v) for v in description[:5])
        out.append({"source": "library_of_congress", "title": x.get("title", "Untitled"), "url": x.get("id") or x.get("url"), "snippet": str(description), "date": x.get("date"), "confidence": 0.9, "provenance": {"api": "loc.gov JSON", "item_id": x.get("item", {}).get("id") if isinstance(x.get("item"), dict) else None}})
    return out


async def nara(q: str, limit: int = 5):
    api_key = os.getenv("TAR_NARA_API_KEY", "")
    if not api_key:
        return []
    try:
        data = await _json("https://catalog.archives.gov/api/v2/records/search", {"q": q, "limit": min(limit, 100)}, headers={"x-api-key": api_key, "Content-Type": "application/json"})
        body = data.get("body", data)
        hits = body.get("hits", {}).get("hits", []) if isinstance(body, dict) else []
        out = []
        for hit in hits[:limit]:
            src = hit.get("_source", hit)
            naid = src.get("naId") or src.get("naid") or src.get("naIdNum")
            title = src.get("title") or src.get("titleNA") or "National Archives record"
            scope = src.get("scopeAndContentNote") or src.get("description") or src.get("recordType") or ""
            if isinstance(scope, dict):
                scope = scope.get("note") or str(scope)
            out.append({"source": "national_archives", "title": str(title), "url": f"https://catalog.archives.gov/id/{naid}" if naid else "https://catalog.archives.gov/", "snippet": str(scope), "confidence": 0.95, "provenance": {"api": "NARA Catalog API v2", "naid": naid}})
        return out
    except Exception:
        return []


async def pubmed(q: str, limit: int = 5):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    common = {"db": "pubmed", "retmode": "json", "tool": "tar-akashic-records"}
    email = os.getenv("TAR_NCBI_EMAIL", "")
    key = os.getenv("TAR_NCBI_API_KEY", "")
    if email:
        common["email"] = email
    if key:
        common["api_key"] = key
    search = await _json(base + "/esearch.fcgi", {**common, "term": q, "retmax": min(limit, 50)})
    ids = search.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    summaries = await _json(base + "/esummary.fcgi", {**common, "id": ",".join(ids)})
    result = summaries.get("result", {})
    out = []
    for pmid in ids:
        x = result.get(str(pmid), {})
        authors = ", ".join(a.get("name", "") for a in x.get("authors", [])[:4] if isinstance(a, dict))
        snippet = " · ".join(v for v in [authors, x.get("fulljournalname", ""), x.get("pubdate", "")] if v)
        out.append({"source": "pubmed", "title": x.get("title", f"PubMed {pmid}"), "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "snippet": snippet, "date": x.get("pubdate"), "confidence": 0.9, "provenance": {"api": "NCBI E-utilities", "pmid": pmid}})
    return out


async def web(q: str, limit: int = 5):
    """Query an operator-controlled SearXNG instance for current web evidence."""
    base = os.getenv("TAR_SEARXNG_URL", "").strip().rstrip("/")
    if not base:
        return []
    params = {"q": q, "format": "json", "language": os.getenv("TAR_SEARXNG_LANGUAGE", "all"), "safesearch": int(os.getenv("TAR_SEARXNG_SAFESEARCH", "1"))}
    data = await _json(f"{base}/search", params)
    out = []
    for x in data.get("results", [])[:limit]:
        url = str(x.get("url", ""))
        if not url.startswith(("http://", "https://")):
            continue
        out.append({
            "source": "web",
            "title": str(x.get("title") or url),
            "url": url,
            "snippet": str(x.get("content") or ""),
            "date": x.get("publishedDate") or x.get("published_date"),
            "confidence": 0.55,
            "provenance": {"api": "SearXNG", "engine": x.get("engine"), "engines": x.get("engines")},
        })
    return out


async def dawes(q: str, limit: int = 5):
    query = f'(Dawes OR "Final Rolls" OR "Five Civilized Tribes") {q}'.strip()
    nara_hits, loc_hits = await asyncio.gather(nara(query, limit), loc(query, limit), return_exceptions=False)
    return [{**x, "source": "dawes_rolls_research"} for x in (nara_hits + loc_hits)[:limit]]


async def freedmen(q: str, limit: int = 5):
    query = f'("Freedmen Bureau" OR "Freedmen’s Bureau" OR "Freedmen records") {q}'.strip()
    nara_hits, loc_hits = await asyncio.gather(nara(query, limit), loc(query, limit), return_exceptions=False)
    return [{**x, "source": "freedmen_records_research"} for x in (nara_hits + loc_hits)[:limit]]


CONNECTORS = {
    "wikipedia": wikipedia,
    "wikidata": wikidata,
    "loc": loc,
    "nara": nara,
    "pubmed": pubmed,
    "web": web,
    "dawes": dawes,
    "freedmen": freedmen,
}


async def search_all(query: str, sources: list[str] | None = None, limit: int = 5):
    defaults = ["web", "wikipedia", "wikidata", "loc", "nara", "pubmed"] if os.getenv("TAR_SEARXNG_URL", "").strip() else ["wikipedia", "wikidata", "loc", "nara", "pubmed"]
    names = sources or defaults
    jobs = [CONNECTORS[n](query, limit) for n in names if n in CONNECTORS]
    groups = await asyncio.gather(*jobs, return_exceptions=True)
    results = []
    seen = set()
    for group in groups:
        if not isinstance(group, list):
            continue
        for item in group:
            key = (item.get("url"), item.get("title"), item.get("source"))
            if key not in seen:
                seen.add(key)
                results.append(item)
    return results
