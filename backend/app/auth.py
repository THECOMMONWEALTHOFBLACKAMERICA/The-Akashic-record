from __future__ import annotations

import os
from fastapi import Header, HTTPException

from .control import verify_api_key


def _extract_key(authorization: str | None, x_tar_api_key: str | None) -> str:
    raw = x_tar_api_key or ""
    if not raw and authorization and authorization.lower().startswith("bearer "):
        raw = authorization[7:].strip()
    return raw


def require_identity(authorization: str | None = Header(default=None), x_tar_api_key: str | None = Header(default=None)) -> dict:
    required = os.getenv("TAR_REQUIRE_API_KEY", "false").lower() in {"1", "true", "yes"}
    raw = _extract_key(authorization, x_tar_api_key)
    if not raw:
        if required:
            raise HTTPException(status_code=401, detail="T.A.R. API key required")
        return {"workspace_id": "default", "label": "anonymous", "key_id": ""}
    identity = verify_api_key(raw)
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid T.A.R. API key")
    return identity


def require_authenticated_identity(authorization: str | None = Header(default=None), x_tar_api_key: str | None = Header(default=None)) -> dict:
    raw = _extract_key(authorization, x_tar_api_key)
    if not raw:
        raise HTTPException(status_code=401, detail="Authenticated T.A.R. API key required")
    identity = verify_api_key(raw)
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid T.A.R. API key")
    return identity
