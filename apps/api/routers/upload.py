import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Project
from schemas import UploadResponse

router = APIRouter(prefix="/api", tags=["upload"])

MAX_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024

MIME_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


def _validate_image_content(content: bytes) -> str:
    try:
        img = Image.open(BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    mime = Image.MIME.get(img.format, "")
    ext = MIME_TO_EXT.get(mime)
    if ext is None:
        raise HTTPException(
            status_code=400,
            detail=f"Image type not supported. Allowed: {', '.join(settings.allowed_extensions)}",
        )
    return ext


@router.post("/upload", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(settings.max_upload_chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.max_upload_size_mb}MB",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    ext = _validate_image_content(content)

    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{ext}"
    upload_dir = Path(settings.storage_path) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / filename
    file_path.write_bytes(content)

    image_url = f"/storage/uploads/{filename}"

    project = Project(image_url=image_url, status="pending")
    db.add(project)
    db.commit()
    db.refresh(project)

    return UploadResponse(
        project_id=project.id,
        image_url=image_url,
        status=project.status,
    )
