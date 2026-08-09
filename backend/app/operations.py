from __future__ import annotations

from fastapi import APIRouter, Depends

from .auth import require_identity
from .provider_status import provider_status

router = APIRouter(prefix="/v1/system", tags=["operations"])


@router.get("/providers")
def providers(identity: dict = Depends(require_identity)):
    # Never return credentials or provider secrets, only configuration presence.
    return provider_status()


@router.get("/capabilities")
def capabilities(identity: dict = Depends(require_identity)):
    providers = provider_status()["configured"]
    return {
        "research": True,
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
