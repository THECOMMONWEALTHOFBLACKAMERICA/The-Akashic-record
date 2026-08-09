from __future__ import annotations

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
    # Never return credentials or provider secrets, only configuration presence.
    result = provider_status()
    result["semantic_retrieval"] = semantic_status()
    return result


@router.get("/storage")
def storage(identity: dict = Depends(require_identity)):
    return configured_storage().health()


@router.get("/capabilities")
def capabilities(identity: dict = Depends(require_identity)):
    providers = provider_status()["configured"]
    semantic = semantic_status()
    storage_status = configured_storage().health()
    return {
        "version": VERSION,
        "research": True,
        "retrieval": {
            "lexical": True,
            "semantic": semantic["active"],
            "semantic_requested": semantic["requested"],
        },
        "artifact_storage": {
            "backend": storage_status.get("backend"),
            "ready": bool(storage_status.get("ok")),
        },
        "ingestion": ["txt", "md", "csv", "json", "pdf", "docx", "xlsx", "pptx"],
        "documents": ["pdf_create", "pdf_merge", "pdf_annotate", "docx_create", "xlsx_create"],
        "distributed_jobs": True,
        "audit_verification": True,
        "media": {
            "image_generation": providers["image"],
            "image_edit": providers["image_edit"],
            "video_generation": providers["video"],
            "transcription": providers["transcription"],
        },
        "archives": {
            "wikipedia": True,
            "wikidata": True,
            "library_of_congress": True,
            "pubmed": True,
            "nara": providers["nara"],
        },
        "governance": providers["governance"],
    }
