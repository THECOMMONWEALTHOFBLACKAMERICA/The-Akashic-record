from __future__ import annotations

import os
import asyncio
import httpx

from .artifacts import save_artifact


class ProviderNotConfigured(RuntimeError):
    pass


async def _download(url: str, headers: dict | None = None) -> bytes:
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        r = await client.get(url, headers=headers or {})
        r.raise_for_status()
        return r.content


async def generate_image(prompt: str, *, size: str = "1024x1024") -> dict:
    endpoint = os.getenv("TAR_IMAGE_API_URL", "").rstrip("/")
    key = os.getenv("TAR_IMAGE_API_KEY", "")
    model = os.getenv("TAR_IMAGE_MODEL", "")
    if not endpoint or not model:
        raise ProviderNotConfigured("Configure TAR_IMAGE_API_URL and TAR_IMAGE_MODEL for an image provider.")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(endpoint, headers=headers, json={"model": model, "prompt": prompt, "size": size})
        r.raise_for_status()
        body = r.json()
    item = (body.get("data") or [{}])[0]
    if item.get("b64_json"):
        import base64
        data = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        data = await _download(item["url"])
    else:
        raise RuntimeError("Image provider returned no supported image payload")
    return save_artifact("generated-image.png", data, "image/png", {"provider_model": model, "prompt": prompt})


async def generate_video(prompt: str, *, seconds: int = 8) -> dict:
    endpoint = os.getenv("TAR_VIDEO_API_URL", "").rstrip("/")
    key = os.getenv("TAR_VIDEO_API_KEY", "")
    model = os.getenv("TAR_VIDEO_MODEL", "")
    if not endpoint or not model:
        raise ProviderNotConfigured("Configure TAR_VIDEO_API_URL and TAR_VIDEO_MODEL for a supported video provider.")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    async with httpx.AsyncClient(timeout=300) as client:
        start = await client.post(endpoint, headers=headers, json={"model": model, "prompt": prompt, "seconds": seconds})
        start.raise_for_status()
        job = start.json()
        result_url = job.get("url") or job.get("output_url")
        status_url = job.get("status_url")
        if not result_url and status_url:
            for _ in range(120):
                await asyncio.sleep(2)
                status = await client.get(status_url, headers=headers)
                status.raise_for_status()
                payload = status.json()
                if payload.get("status") in {"failed", "error"}:
                    raise RuntimeError(str(payload))
                result_url = payload.get("url") or payload.get("output_url")
                if result_url:
                    break
        if not result_url:
            raise RuntimeError("Video provider did not return a completed output URL")
    data = await _download(result_url, headers=headers if result_url.startswith(endpoint) else None)
    return save_artifact("generated-video.mp4", data, "video/mp4", {"provider_model": model, "prompt": prompt, "seconds": seconds})
