from __future__ import annotations

from .commission import add_evidence, export_case
from .retrieval import hybrid_recall
from .sources import search_all

OFFICIAL_SOURCES = ["nara", "loc", "freedmen"]
BROAD_SOURCES = ["web", "wikipedia", "wikidata"]


async def research_case(
    case_id: str,
    workspace_id: str,
    query: str,
    *,
    include_dawes: bool = False,
    broaden_web: bool = False,
    persist_as_evidence: bool = True,
    actor: str = "system",
    limit: int = 5,
) -> dict:
    exported = export_case(case_id, workspace_id)
    case = exported["case"]

    # Search workspace-scoped ingested/vetted material first. This is not
    # automatically promoted to a legal evidentiary tier; reviewers decide.
    local_hits = hybrid_recall(query, limit=max(1, min(limit, 25)), workspace_id=workspace_id)

    sources = list(OFFICIAL_SOURCES)
    if include_dawes:
        sources.append("dawes")
    if broaden_web:
        sources.extend(BROAD_SOURCES)
    elif not case.get("restricted_research", True):
        sources.extend(BROAD_SOURCES)

    remote_hits = await search_all(query, sources=sources, limit=max(1, min(limit, 25)))
    results: list[dict] = []
    seen: set[tuple] = set()
    for item in local_hits + remote_hits:
        key = (item.get("url"), item.get("document_id"), item.get("chunk_id"), item.get("title"), item.get("source"))
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    evidence = []
    if persist_as_evidence:
        for item in results:
            source = str(item.get("source") or "")
            # Official/government or previously ingested records enter the case
            # as Tier 1 only when the connector/source is primary-record oriented.
            # General web/discovery material is Tier 2. Human review can still
            # mark any item insufficient/excluded/conflicting.
            tier = 1 if source in {"national_archives", "library_of_congress", "freedmen_records_research", "dawes_rolls_research"} or item.get("document_id") else 2
            evidence.append(
                add_evidence(
                    case_id,
                    workspace_id,
                    title=str(item.get("title") or "Retrieved record"),
                    source_tier=tier,
                    source=source,
                    source_uri=str(item.get("url") or ""),
                    citation=str(item.get("citation") or item.get("url") or ""),
                    retrieval_metadata={
                        "query": query,
                        "provenance": item.get("provenance") or {},
                        "date": item.get("date"),
                        "document_id": item.get("document_id"),
                        "chunk_id": item.get("chunk_id"),
                        "retrieval_score": item.get("retrieval_score"),
                    },
                    claimed_provenance="T.A.R.-retrieved; pending Commission verification",
                    media_type="text/plain",
                    actor=actor,
                )
            )

    return {
        "case_id": case_id,
        "workspace_id": workspace_id,
        "restricted_research": case.get("restricted_research", True),
        "broad_web_used": broaden_web or not case.get("restricted_research", True),
        "sources_requested": sources,
        "results": results,
        "evidence_created": evidence,
    }
