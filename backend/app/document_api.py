from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .auth import require_identity
from .control import audit
from .document_tools import annotate_pdf, create_docx, create_pdf, create_xlsx, merge_pdfs

router = APIRouter(prefix="/v1/doc-tools", tags=["documents"])


class TextDocumentRequest(BaseModel):
    title: str = Field(default="TAR Document", max_length=500)
    text: str = Field(min_length=1, max_length=1_000_000)


class SpreadsheetRequest(BaseModel):
    name: str = Field(default="data.xlsx", max_length=500)
    rows: list[dict] = Field(default_factory=list)


@router.post("/pdf")
def make_pdf(req: TextDocumentRequest, identity: dict = Depends(require_identity)):
    artifact = create_pdf(req.title, req.text, identity["workspace_id"])
    audit("document.pdf_created", "artifact", artifact["artifact_id"], {"title": req.title}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return artifact


@router.post("/docx")
def make_docx(req: TextDocumentRequest, identity: dict = Depends(require_identity)):
    artifact = create_docx(req.title, req.text, identity["workspace_id"])
    audit("document.docx_created", "artifact", artifact["artifact_id"], {"title": req.title}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return artifact


@router.post("/xlsx")
def make_xlsx(req: SpreadsheetRequest, identity: dict = Depends(require_identity)):
    artifact = create_xlsx(req.rows, req.name, identity["workspace_id"])
    audit("document.xlsx_created", "artifact", artifact["artifact_id"], {"rows": len(req.rows)}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return artifact


@router.post("/pdf/merge")
async def pdf_merge(files: list[UploadFile] = File(...), identity: dict = Depends(require_identity)):
    if len(files) < 2 or len(files) > 25:
        raise HTTPException(status_code=400, detail="Provide between 2 and 25 PDFs")
    payloads=[]
    for file in files:
        data=await file.read()
        if not data.startswith(b"%PDF"):raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF")
        payloads.append(data)
    artifact=merge_pdfs(payloads, workspace_id=identity["workspace_id"])
    audit("document.pdf_merged", "artifact", artifact["artifact_id"], {"files": len(payloads)}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return artifact


@router.post("/pdf/annotate")
async def pdf_annotate(file: UploadFile = File(...), page: int = Form(...), text: str = Form(...), x: float = Form(default=50), y: float = Form(default=50), identity: dict = Depends(require_identity)):
    data=await file.read()
    try:artifact=annotate_pdf(data,page,text,x,y,identity["workspace_id"])
    except Exception as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    audit("document.pdf_annotated", "artifact", artifact["artifact_id"], {"page": page, "filename": file.filename}, workspace_id=identity["workspace_id"], actor=identity["label"])
    return artifact
