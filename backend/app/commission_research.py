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
    existing_evidence = exported.get("evidence") or []
    existing_keys = {
        (str(e.get("source") or ""), str(e.get("source_uri") or ""), str(e.get("title") or ""))
        for e in existing_evidence
    }

    # Search workspace-scoped ingested/vetted material first. Local corpus hits
    # are still pending human classification unless their provenance already
    # establishes the source tier.
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
    skipped_existing = 0
    if persist_as_evidence:
        for item in results:
            source = str(item.get("source") or "")
            source_uri = str(item.get("url") or "")
            title = str(item.get("title") or "Retrieved record")
            evidence_key = (source, source_uri, title)
            if evidence_key in existing_keys:
                skipped_existing += 1
                continue

            # NARA, purpose-built Freedmen/Final Rolls results and already-vetted
            # ingested records may begin as Tier 1 candidates. Library of Congress
            # and general discovery sources begin at Tier 2 because LOC holdings
            # can include both primary and published/corroborating material.
            # Commissioners can correct the source tier during review.
            tier = 1 if source in {"national_archives", "freedmen_records_research", "dawes_rolls_research"} or item.get("document_id") else 2
            created = add_evidence(
                case_id,
                workspace_id,
                title=title,
                source_tier=tier,
                source=source,
                source_uri=source_uri,
                citation=str(item.get("citation") or source_uri),
                retrieval_metadata={
                    "query": query,
                    "provenance": item.get("provenance") or {},
                    "date": item.get("date"),
                    "document_id": item.get("document_id"),
                    "chunk_id": item.get("chunk_id"),
                    "retrieval_score": item.get("retrieval_score"),
                    "tier_is_initial_classification": True,
                },
                claimed_provenance="T.A.R.-retrieved; pending Commission verification",
                media_type="text/plain",
                actor=actor,
            )
            evidence.append(created)
            existing_keys.add(evidence_key)

    return {
        "case_id": case_id,
        "workspace_id": workspace_id,
        "restricted_research": case.get("restricted_research", True),
        "broad_web_used": broaden_web or not case.get("restricted_research", True),
        "sources_requested": sources,
        "results": results,
        "evidence_created": evidence,
        "evidence_skipped_existing": skipped_existing,
    }
