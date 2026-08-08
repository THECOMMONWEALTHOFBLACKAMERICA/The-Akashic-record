import asyncio
import httpx
from .settings import settings

HEADERS = {"User-Agent": "TAR-Akashic-Records/0.1 (research client)"}

async def _json(url: str, params: dict):
    async with httpx.AsyncClient(timeout=settings.request_timeout, headers=HEADERS, follow_redirects=True) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()

async def wikipedia(q: str, limit: int = 5):
    data = await _json("https://en.wikipedia.org/w/api.php", {"action":"query","list":"search","srsearch":q,"format":"json","utf8":1,"srlimit":limit})
    return [{"source":"wikipedia","title":x["title"],"url":f"https://en.wikipedia.org/wiki/{x['title'].replace(' ', '_')}","snippet":x.get("snippet","")} for x in data.get("query",{}).get("search",[])]

async def wikidata(q: str, limit: int = 5):
    data = await _json("https://www.wikidata.org/w/api.php", {"action":"wbsearchentities","search":q,"language":"en","format":"json","limit":limit})
    return [{"source":"wikidata","title":x.get("label",x["id"]),"url":f"https://www.wikidata.org/wiki/{x['id']}","snippet":x.get("description","")} for x in data.get("search",[])]

async def loc(q: str, limit: int = 5):
    data = await _json("https://www.loc.gov/search/", {"q":q,"fo":"json","c":limit})
    return [{"source":"library_of_congress","title":x.get("title","Untitled"),"url":x.get("id") or x.get("url"),"snippet":str(x.get("description","") or "")} for x in data.get("results",[])[:limit]]

async def nara(q: str, limit: int = 5):
    # NARA's catalog/API evolves; this adapter fails closed so one unavailable archive never breaks research.
    try:
        data = await _json("https://catalog.archives.gov/proxy/records/search", {"q":q,"limit":limit})
        body = data.get("body", data)
        hits = body.get("hits",{}).get("hits",[]) if isinstance(body, dict) else []
        out=[]
        for hit in hits[:limit]:
            src=hit.get("_source",{})
            naid=src.get("naId") or src.get("naid")
            out.append({"source":"national_archives","title":src.get("title","NARA record"),"url":f"https://catalog.archives.gov/id/{naid}" if naid else "https://catalog.archives.gov/","snippet":str(src.get("scopeAndContentNote","") or "")})
        return out
    except Exception:
        return []

CONNECTORS={"wikipedia":wikipedia,"wikidata":wikidata,"loc":loc,"nara":nara}

async def search_all(query: str, sources: list[str] | None = None, limit: int = 5):
    names=sources or list(CONNECTORS)
    jobs=[CONNECTORS[n](query,limit) for n in names if n in CONNECTORS]
    groups=await asyncio.gather(*jobs, return_exceptions=True)
    results=[]
    for group in groups:
        if isinstance(group,list): results.extend(group)
    return results
