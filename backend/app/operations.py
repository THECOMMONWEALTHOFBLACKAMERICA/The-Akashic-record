from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from .auth import require_identity
from .provider_status import provider_status
from .semantic import status as semantic_status
from .storage import configured_storage
from .version import VERSION

router = APIRouter(prefix="/v1/system", tags=["operations"])


@router.get("/version")
def version():
    return {"service": "tar-api", "version": VERSION}


@router.get("/providers")
def providers(identity: dict = Depends(require_identity)):
    result = provider_status()
    result["semantic_retrieval"] = semantic_status()
    result["web_search"] = {"configured": bool(os.getenv("TAR_SEARXNG_URL", "").strip()), "provider": "searxng"}
    return result


@router.get("/storage")
def storage(identity: dict = Depends(require_identity)):
    return configured_storage().health()


@router.get("/capabilities")
def capabilities(identity: dict = Depends(require_identity)):
    providers = provider_status()["configured"]
    semantic = semantic_status()
    storage_status = configured_storage().health()
    web_configured = bool(os.getenv("TAR_SEARXNG_URL", "").strip())
    return {
        "version": VERSION,
        "research": True,
        "retrieval": {
            "lexical": True,
            "semantic": semantic["active"],
            "semantic_requested": semantic["requested"],
            "current_web": web_configured,
        },
        "artifact_storage": {
            "backend": storage_status.get("backend"),
            "ready": bool(storage_status.get("ok")),
        },
        "ingestion": ["txt", "md", "csv", "json", "pdf", "epub", "docx", "xlsx", "pptx"],
        "documents": ["pdf_create", "pdf_merge", "pdf_annotate", "docx_create", "xlsx_create"],
        "distributed_jobs": True,
        "audit_verification": True,
        "media": {
            "image_generation": providers["image"],
            "image_edit": providers["image_edit"],
            "video_generation": providers["video"],
            "transcription": providers["transcription"],
        },
        "sources": {
            "current_web": web_configured,
            "wikipedia": True,
            "wikidata": True,
            "library_of_congress": True,
            "pubmed": True,
            "nara": providers["nara"],
            "dawes_strategy": True,
            "freedmen_strategy": True,
        },
        "governance": providers["governance"],
    }
