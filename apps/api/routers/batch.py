import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import require_auth
from config import settings
from database import get_db
from models import Job, Project, User
from routers.usage import PLAN_LIMITS, check_usage_limit, increment_usage

router = APIRouter(prefix="/api/batch", tags=["batch"])

MIME_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}

MAX_BATCH_SIZE = {
    "free": 0,
    "basic": 5,
    "pro": 20,
}


class BatchUploadResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    project_ids: list[str]
    errors: list[str]


def _validate_image(content: bytes) -> str:
    try:
        img = Image.open(BytesIO(content))
        img.verify()
    except Exception:
        raise ValueError("Invalid image file")
    mime = Image.MIME.get(img.format, "")
    ext = MIME_TO_EXT.get(mime)
    if ext is None:
        raise ValueError("Unsupported image type")
    return ext


@router.post("/upload", response_model=BatchUploadResult)
async def batch_upload(
    files: list[UploadFile] = File(...),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    max_batch = MAX_BATCH_SIZE.get(user.plan_type, 0)
    if max_batch == 0:
        raise HTTPException(
            status_code=403,
            detail="Batch upload requires a paid plan",
        )

    if len(files) > max_batch:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_batch} files per batch for {user.plan_type} plan",
        )

    project_ids: list[str] = []
    errors: list[str] = []
    max_size = settings.max_upload_size_mb * 1024 * 1024

    for file in files:
        try:
            if not check_usage_limit(user, db):
                errors.append(f"{file.filename}: Usage limit exceeded")
                continue

            content = await file.read()
            if len(content) > max_size:
                errors.append(f"{file.filename}: File too large")
                continue

            ext = _validate_image(content)

            file_id = str(uuid.uuid4())
            filename = f"{file_id}.{ext}"
            upload_dir = Path(settings.storage_path) / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            (upload_dir / filename).write_bytes(content)

            image_url = f"/storage/uploads/{filename}"
            project = Project(
                user_id=user.id,
                image_url=image_url,
                status="pending",
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            job = Job(project_id=project.id, status="queued")
            db.add(job)
            db.commit()

            increment_usage(user, db)

            try:
                from worker import process_image
                process_image.delay(str(project.id), str(upload_dir / filename))
            except Exception:
                pass

            project_ids.append(str(project.id))

        except ValueError as e:
            errors.append(f"{file.filename}: {str(e)}")
        except Exception as e:
            errors.append(f"{file.filename}: Processing error")

    return BatchUploadResult(
        total=len(files),
        succeeded=len(project_ids),
        failed=len(errors),
        project_ids=project_ids,
        errors=errors,
    )


@router.get("/status")
async def batch_status(
    project_ids: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    ids = [pid.strip() for pid in project_ids.split(",") if pid.strip()]

    results = []
    for pid in ids:
        project = db.query(Project).filter(Project.id == pid).first()
        if not project:
            results.append({"id": pid, "status": "not_found"})
            continue

        job = db.query(Job).filter(Job.project_id == pid).order_by(Job.id.desc()).first()
        results.append({
            "id": pid,
            "status": project.status,
            "stage": job.status if job else "unknown",
        })

    completed = sum(1 for r in results if r["status"] == "done")
    total = len(results)

    return {
        "total": total,
        "completed": completed,
        "progress": round(completed / max(total, 1) * 100),
        "projects": results,
    }
