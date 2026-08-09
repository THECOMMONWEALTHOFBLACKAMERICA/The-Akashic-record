from __future__ import annotations

import os


def provider_status() -> dict:
    checks = {
        "llm": bool(os.getenv("TAR_LLM_BASE_URL") and os.getenv("TAR_LLM_MODEL")),
        "image": bool(os.getenv("TAR_IMAGE_API_URL") and os.getenv("TAR_IMAGE_MODEL")),
        "image_edit": bool(os.getenv("TAR_IMAGE_EDIT_API_URL") and (os.getenv("TAR_IMAGE_EDIT_MODEL") or os.getenv("TAR_IMAGE_MODEL"))),
        "video": bool(os.getenv("TAR_VIDEO_API_URL") and os.getenv("TAR_VIDEO_MODEL")),
        "transcription": bool(os.getenv("TAR_TRANSCRIBE_API_URL") and os.getenv("TAR_TRANSCRIBE_MODEL")),
        "nara": bool(os.getenv("TAR_NARA_API_KEY")),
        "governance": bool(os.getenv("TAR_CHAIN_RPC_URL") and os.getenv("TAR_GOVERNANCE_ADDRESS")),
    }
    return {"configured": checks, "configured_count": sum(checks.values()), "total": len(checks)}
