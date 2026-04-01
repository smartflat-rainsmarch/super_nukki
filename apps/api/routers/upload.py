import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Job, Project
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

    job = Job(project_id=project.id, status="queued")
    db.add(job)
    db.commit()

    # Try Celery worker first, fall back to sync processing
    celery_dispatched = False
    try:
        from worker import process_image
        process_image.delay(str(project.id), str(file_path))
        celery_dispatched = True
    except Exception:
        pass

    if not celery_dispatched:
        _run_pipeline_sync(str(project.id), str(file_path), db)

    db.refresh(project)

    return UploadResponse(
        project_id=project.id,
        image_url=image_url,
        status=project.status,
    )


def _run_pipeline_sync(project_id: str, image_path: str, db: Session):
    from models import Layer, Project as ProjectModel

    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    job = db.query(Job).filter(Job.project_id == project_id).first()

    try:
        if project:
            project.status = "processing"
            db.commit()
        if job:
            job.status = "analyzing"
            db.commit()

        output_dir = str(Path(settings.storage_path) / "outputs" / project_id)
        from engine.pipeline import run_pipeline
        run_pipeline(image_path, output_dir)

        _populate_layers_from_manifest(project_id, output_dir, db)

        if job:
            job.status = "completed"
            db.commit()
        if project:
            project.status = "done"
            db.commit()

    except Exception as e:
        if job:
            job.status = "failed"
            db.commit()
        if project:
            project.status = "failed"
            db.commit()


def _populate_layers_from_manifest(project_id: str, output_dir: str, db: Session):
    import json
    from models import Layer

    manifest_path = Path(output_dir) / "layers" / "manifest.json"
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text())

    valid_types = {"text", "button", "image", "icon", "card", "background"}

    for layer_data in manifest.get("layers", []):
        bbox = layer_data.get("bbox", {})
        raw_type = layer_data.get("type", "image")
        layer_type = raw_type if raw_type in valid_types else "image"

        image_filename = Path(layer_data.get("image_path", "")).name
        image_url = f"/storage/outputs/{project_id}/layers/{image_filename}"

        layer = Layer(
            project_id=project_id,
            type=layer_type,
            position={
                "x": bbox.get("x", 0),
                "y": bbox.get("y", 0),
                "w": bbox.get("w", 0),
                "h": bbox.get("h", 0),
            },
            image_url=image_url,
            text_content=layer_data.get("text_content"),
            z_index=layer_data.get("z_index", 0),
        )
        db.add(layer)

    db.commit()
