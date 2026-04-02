from __future__ import annotations

import os
import re
import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import get_current_user
from app.models import User
from app.schemas.session import UploadImageResponse

router = APIRouter()

ROOT = Path(__file__).resolve().parents[2]
LOCAL_UPLOAD_DIR = Path(os.getenv("LOCAL_UPLOAD_DIR", str(ROOT / "storage" / "uploads"))).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", "10485760"))  # 10 MB
PUBLIC_UPLOAD_BASE_URL = os.getenv("PUBLIC_UPLOAD_BASE_URL", "http://127.0.0.1:8000")


def _sanitize_file_name(file_name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "-", file_name.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "upload.png"


def _assert_image_content_type(content_type: str | None) -> str:
    if not content_type or not content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="image file only")
    return content_type


def _save_local_file(*, file_id: str, file_name: str, file_bytes: bytes) -> Path:
    target_dir = (LOCAL_UPLOAD_DIR / file_id).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = (target_dir / file_name).resolve()
    if target_path.parent != target_dir:
        raise HTTPException(status_code=400, detail="invalid file path")
    target_path.write_bytes(file_bytes)
    return target_path


@router.post("/api/uploads/images", response_model=UploadImageResponse)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> UploadImageResponse:
    _ = current_user
    content_type = _assert_image_content_type(file.content_type)
    safe_file_name = _sanitize_file_name(file.filename or "upload.png")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"file too large: max {MAX_UPLOAD_BYTES} bytes")

    file_id = str(uuid4())
    _save_local_file(file_id=file_id, file_name=safe_file_name, file_bytes=data)
    public_url = f"{PUBLIC_UPLOAD_BASE_URL}/api/uploads/files/{file_id}/{safe_file_name}"
    return UploadImageResponse(fileId=file_id, url=public_url, contentType=content_type)


@router.get("/api/uploads/files/{file_id}/{file_name}")
def get_uploaded_file(file_id: str, file_name: str) -> FileResponse:
    safe_file_name = _sanitize_file_name(file_name)
    if safe_file_name != file_name:
        raise HTTPException(status_code=404, detail="file not found")

    file_path = (LOCAL_UPLOAD_DIR / file_id / safe_file_name).resolve()
    if LOCAL_UPLOAD_DIR not in file_path.parents:
        raise HTTPException(status_code=404, detail="file not found")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="file not found")

    media_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)
