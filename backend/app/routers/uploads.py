from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from app.schemas.session import UploadImageRequest, UploadImageResponse

router = APIRouter()


@router.post("/api/uploads/images", response_model=UploadImageResponse)
def upload_image_stub(payload: UploadImageRequest) -> UploadImageResponse:
    file_id = uuid4()
    safe_file_name = payload.fileName.strip().replace(" ", "-")
    return UploadImageResponse(
        fileId=str(file_id),
        url=f"https://storage.example.com/uploads/{file_id}/{safe_file_name}",
        contentType=payload.contentType,
    )
