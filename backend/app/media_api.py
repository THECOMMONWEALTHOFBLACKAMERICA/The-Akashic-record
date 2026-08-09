from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from .auth import require_identity
from .control import audit
from .media import ProviderNotConfigured, edit_image, transcribe_audio

router = APIRouter(prefix="/v1/media", tags=["media"])


@router.post("/image/edit")
async def image_edit(file: UploadFile = File(...), prompt: str = Form(...), identity: dict = Depends(require_identity)):
    data = await file.read()
    try:
        artifact = await edit_image(data, prompt, filename=file.filename or "image.png")
    except (ProviderNotConfigured, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit("media.image_edited", "artifact", artifact["artifact_id"], {"filename": file.filename}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return artifact


@router.post("/audio/transcribe")
async def audio_transcribe(file: UploadFile = File(...), language: str | None = Form(default=None), identity: dict = Depends(require_identity)):
    data = await file.read()
    try:
        result = await transcribe_audio(data, filename=file.filename or "audio.wav", language=language)
    except (ProviderNotConfigured, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit("media.audio_transcribed", "artifact", result["artifact"]["artifact_id"], {"filename": file.filename, "language": language}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return result
