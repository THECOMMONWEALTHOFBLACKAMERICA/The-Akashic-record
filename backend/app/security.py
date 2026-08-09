from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Header, HTTPException


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest() if raw else ""


def _verify_secret(configured_raw: str, supplied_raw: str | None) -> bool:
    if not configured_raw:
        return False
    return hmac.compare_digest(_digest(configured_raw), _digest(supplied_raw or ""))


def require_admin(x_tar_admin_key: str | None = Header(default=None)) -> dict:
    configured = os.getenv("TAR_ADMIN_KEY", "")
    if not configured:
        raise HTTPException(status_code=503, detail="Administrative API is disabled until TAR_ADMIN_KEY is configured")
    if not _verify_secret(configured, x_tar_admin_key):
        raise HTTPException(status_code=403, detail="Administrator authorization required")
    return {"role": "admin", "label": "administrator", "workspace_id": "default"}


def require_worker(x_tar_worker_key: str | None = Header(default=None)) -> dict:
    configured = os.getenv("TAR_WORKER_KEY", "")
    if not configured:
        raise HTTPException(status_code=503, detail="Remote worker API is disabled until TAR_WORKER_KEY is configured")
    if not _verify_secret(configured, x_tar_worker_key):
        raise HTTPException(status_code=403, detail="Worker authorization required")
    return {"role": "worker", "label": "remote-worker"}
