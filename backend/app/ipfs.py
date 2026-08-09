from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import httpx


class IPFSPublicationDisabled(RuntimeError):
    pass


class IPFSError(RuntimeError):
    pass


def enabled() -> bool:
    return os.getenv("TAR_ENABLE_PUBLIC_IPFS", "false").lower() in {"1", "true", "yes"}


def api_url() -> str:
    return os.getenv("TAR_IPFS_API_URL", "http://ipfs:5001").rstrip("/")


def gateway_url() -> str:
    return os.getenv("TAR_IPFS_GATEWAY", "http://localhost:8080/ipfs").rstrip("/")


def _require_enabled() -> None:
    if not enabled():
        raise IPFSPublicationDisabled(
            "Public IPFS publication is disabled. Set TAR_ENABLE_PUBLIC_IPFS=true only when operators intentionally allow immutable/public publication."
        )


def add_bytes(data: bytes, filename: str, media_type: str = "application/octet-stream") -> dict:
    _require_enabled()
    url = api_url() + "/api/v0/add"
    params = {"pin": "true", "cid-version": "1", "raw-leaves": "true", "wrap-with-directory": "false"}
    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(url, params=params, files={"file": (filename, data, media_type)})
            response.raise_for_status()
    except Exception as exc:
        raise IPFSError(f"IPFS add failed: {exc}") from exc

    # Kubo may emit newline-delimited JSON when adding multiple files. The final
    # non-empty object is the root/result relevant to this single-file request.
    objects = []
    for line in response.text.splitlines():
        line = line.strip()
        if line:
            objects.append(json.loads(line))
    if not objects or not objects[-1].get("Hash"):
        raise IPFSError("IPFS daemon returned no CID")
    cid = objects[-1]["Hash"]
    return {
        "cid": cid,
        "name": objects[-1].get("Name", filename),
        "size": int(objects[-1].get("Size", len(data))),
        "gateway_url": f"{gateway_url()}/{cid}",
    }


def publish_manifest(manifest: dict) -> dict:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return add_bytes(canonical, "tar-provenance.json", "application/json")


def status() -> dict:
    result = {"enabled": enabled(), "api": api_url(), "gateway": gateway_url()}
    if not enabled():
        result["reachable"] = False
        return result
    try:
        with httpx.Client(timeout=5) as client:
            response = client.post(api_url() + "/api/v0/id")
            response.raise_for_status()
            body = response.json()
        result.update({"reachable": True, "peer_id": body.get("ID", "")})
    except Exception as exc:
        result.update({"reachable": False, "error": str(exc)})
    return result


def manifest_for_artifact(*, artifact_id: str, workspace_id: str, name: str, media_type: str, sha256: str, size_bytes: int, artifact_cid: str, version: str) -> dict:
    return {
        "schema": "tar.provenance.artifact.v1",
        "artifact_id": artifact_id,
        "workspace_id": workspace_id,
        "name": name,
        "media_type": media_type,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "artifact_cid": artifact_cid,
        "tar_version": version,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
