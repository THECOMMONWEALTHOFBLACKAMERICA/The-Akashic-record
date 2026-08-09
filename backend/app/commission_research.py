from __future__ import annotations

from .commission import add_evidence, export_case
from .sources import search_all

OFFICIAL_SOURCES = ["nara", "loc", "freedmen"]
BROAD_SOURCES = ["web", "wikipedia", "wikidata"]


def _case_local_hits(query: str, evidence: list[dict], limit: int) -> list[dict]:
    """Search only evidence already belonging to this case.

    Commission research must never use workspace-wide recall because a Commission
    workspace can contain multiple applicant cases. A future shared reference
    corpus must have its own explicit vetted namespace before it is queried here.
    """
    tokens = {t.lower() for t in query.split() if len(t) > 2}
    scored: list[tuple[int, dict]] = []
    for item in evidence:
        haystack = " ".join(
            str(item.get(k) or "")
            for k in ["title", "source", "source_uri", "citation", "claimed_provenance", "review_notes"]
        ).lower()
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored.append(
                (
                    score,
                    {
                        "source": "commission_case_evidence",
                        "title": item.get("title") or "Case evidence",
                        "url": item.get("source_uri") or "",
                        "snippet": item.get("citation") or item.get("claimed_provenance") or "Existing case evidence",
                        "confidence": 1.0,
                        "case_evidence_id": item.get("evidence_id"),
                        "source_tier": item.get("source_tier"),
                        "status": item.get("status"),
                        "provenance": {"case_local": True},
                    },
                )
            )
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


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

    local_hits = _case_local_hits(query, existing_evidence, max(1, min(limit, 25)))

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
        key = (item.get("url"), item.get("case_evidence_id"), item.get("title"), item.get("source"))
        if key in seen:
            continue
        seen.add(key)
        results.append(item)

    evidence = []
    skipped_existing = 0
    if persist_as_evidence:
        for item in remote_hits:
            # Existing case-local evidence is returned for context but is not
            # reinserted as a new evidence row.
            source = str(item.get("source") or "")
            source_uri = str(item.get("url") or "")
            title = str(item.get("title") or "Retrieved record")
            evidence_key = (source, source_uri, title)
            if evidence_key in existing_keys:
                skipped_existing += 1
                continue

            tier = 1 if source in {"national_archives", "freedmen_records_research", "dawes_rolls_research"} else 2
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
        "workspace_wide_recall_used": False,
    }
