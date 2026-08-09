from __future__ import annotations

import hashlib
import hmac
import os
from fastapi import Header, HTTPException


def _configured_admin_hash() -> str:
    raw = os.getenv("TAR_ADMIN_KEY", "")
    return hashlib.sha256(raw.encode()).hexdigest() if raw else ""


def require_admin(x_tar_admin_key: str | None = Header(default=None)) -> dict:
    configured = _configured_admin_hash()
    if not configured:
        raise HTTPException(status_code=503, detail="Administrative API is disabled until TAR_ADMIN_KEY is configured")
    supplied = hashlib.sha256((x_tar_admin_key or "").encode()).hexdigest()
    if not hmac.compare_digest(configured, supplied):
        raise HTTPException(status_code=403, detail="Administrator authorization required")
    return {"role": "admin", "label": "administrator", "workspace_id": "default"}
