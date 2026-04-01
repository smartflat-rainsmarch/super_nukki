from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Job, Layer, Project, User

router = APIRouter(prefix="/api", tags=["project"])


@router.get("/project/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = db.query(Job).filter(Job.project_id == pid).order_by(Job.id.desc()).first()

    progress = 0
    stage = "pending"
    if job:
        stage = job.status
        stage_progress = {
            "queued": 0,
            "preprocessing": 10,
            "analyzing": 30,
            "segmenting": 50,
            "inpainting": 70,
            "composing": 85,
            "exporting": 95,
            "completed": 100,
            "failed": 0,
        }
        progress = stage_progress.get(job.status, 0)

    return {
        "id": str(project.id),
        "image_url": project.image_url,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "stage": stage,
        "progress": progress,
    }


@router.get("/project/{project_id}/result")
async def get_project_result(project_id: str, db: Session = Depends(get_db)):
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    layers = db.query(Layer).filter(Layer.project_id == pid).order_by(Layer.z_index).all()

    psd_url = f"/api/download/{project_id}" if project.status == "done" else None

    canvas_size = _get_canvas_size(str(pid))

    return {
        "id": str(project.id),
        "image_url": project.image_url,
        "status": project.status,
        "psd_url": psd_url,
        "canvas_size": canvas_size,
        "notice": "이 결과는 AI가 생성한 편집 가능한 초안입니다. 완벽한 복원을 보장하지 않습니다.",
        "layers": [
            {
                "id": str(l.id),
                "type": l.type,
                "position": l.position,
                "image_url": l.image_url,
                "text_content": l.text_content,
                "z_index": l.z_index,
                "layer_kind": "editable" if l.type == "text" else "raster",
            }
            for l in layers
        ],
    }


def _get_canvas_size(project_id: str) -> dict:
    import json
    from pathlib import Path
    from config import settings

    manifest_path = Path(settings.storage_path) / "outputs" / project_id / "layers" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        cs = manifest.get("canvas_size", {})
        return {"width": cs.get("width", 400), "height": cs.get("height", 700)}

    return {"width": 400, "height": 700}
