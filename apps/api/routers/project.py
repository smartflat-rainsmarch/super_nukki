import json
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from config import settings
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
            "queued": 0, "preprocessing": 10, "analyzing": 30,
            "segmenting": 50, "inpainting": 70, "composing": 85,
            "exporting": 95, "completed": 100, "failed": 0,
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

    # Get root layers (no parent)
    root_layers = (
        db.query(Layer)
        .filter(Layer.project_id == pid, Layer.parent_id == None)
        .order_by(Layer.z_index)
        .all()
    )

    psd_url = f"/api/download/{project_id}" if project.status == "done" else None
    canvas_size = _get_canvas_size(str(pid))

    def layer_to_dict(layer, depth=0):
        if depth > 3:
            return {"id": str(layer.id), "type": layer.type, "position": layer.position, "image_url": layer.image_url, "text_content": layer.text_content, "z_index": layer.z_index, "layer_kind": "editable" if layer.type == "text" else "raster", "parent_id": str(layer.parent_id) if layer.parent_id else None, "children": []}
        children = (
            db.query(Layer)
            .filter(Layer.parent_id == layer.id)
            .order_by(Layer.z_index)
            .all()
        )
        return {
            "id": str(layer.id),
            "type": layer.type,
            "position": layer.position,
            "image_url": layer.image_url,
            "text_content": layer.text_content,
            "z_index": layer.z_index,
            "layer_kind": "editable" if layer.type == "text" else "raster",
            "parent_id": str(layer.parent_id) if layer.parent_id else None,
            "children": [layer_to_dict(c, depth + 1) for c in children],
        }

    return {
        "id": str(project.id),
        "image_url": project.image_url,
        "status": project.status,
        "psd_url": psd_url,
        "canvas_size": canvas_size,
        "notice": "이 결과는 AI가 생성한 편집 가능한 초안입니다. 완벽한 복원을 보장하지 않습니다.",
        "layers": [layer_to_dict(l) for l in root_layers],
    }


@router.post("/project/{project_id}/layer/{layer_id}/decompose")
async def decompose_layer(
    project_id: str,
    layer_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    layer = db.query(Layer).filter(Layer.id == layer_id, Layer.project_id == project_id).first()
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    if not layer.image_url:
        raise HTTPException(status_code=400, detail="Layer has no image to decompose")

    # Check if already decomposed
    existing_children = db.query(Layer).filter(Layer.parent_id == layer_id).count()
    if existing_children > 0:
        raise HTTPException(status_code=400, detail="Layer already decomposed")

    # Resolve image path safely
    url_path = layer.image_url.replace("/storage/", "", 1) if layer.image_url.startswith("/storage/") else layer.image_url
    image_path = (Path(settings.storage_path) / url_path).resolve()
    storage_root = Path(settings.storage_path).resolve()
    if not str(image_path).startswith(str(storage_root)):
        raise HTTPException(status_code=400, detail="Invalid layer path")
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Layer image file not found")

    # Run sub-pipeline on this layer image
    sub_output_dir = Path(settings.storage_path) / "outputs" / project_id / "sub" / layer_id
    sub_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from engine.pipeline import run_pipeline
        result = run_pipeline(str(image_path), str(sub_output_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail="레이어 변환에 실패했습니다. 다시 시도해주세요.")

    # Read manifest and create child layers
    manifest_path = sub_output_dir / "layers" / "manifest.json"
    if not manifest_path.exists():
        return {"children": [], "count": 0}

    manifest = json.loads(manifest_path.read_text())
    valid_types = {"text", "button", "image", "icon", "card", "background"}
    children = []

    parent_pos = layer.position or {"x": 0, "y": 0}

    for ld in manifest.get("layers", []):
        bbox = ld.get("bbox", {})
        raw_type = ld.get("type", "image")
        layer_type = raw_type if raw_type in valid_types else "image"

        image_filename = Path(ld.get("image_path", "")).name
        image_url = f"/storage/outputs/{project_id}/sub/{layer_id}/layers/{image_filename}"

        # Offset child positions relative to parent
        child = Layer(
            project_id=project_id,
            parent_id=layer_id,
            type=layer_type,
            position={
                "x": parent_pos.get("x", 0) + bbox.get("x", 0),
                "y": parent_pos.get("y", 0) + bbox.get("y", 0),
                "w": bbox.get("w", 0),
                "h": bbox.get("h", 0),
            },
            image_url=image_url,
            text_content=ld.get("text_content"),
            z_index=ld.get("z_index", 0),
        )
        db.add(child)
        children.append({
            "type": layer_type,
            "position": child.position,
            "image_url": image_url,
            "text_content": child.text_content,
        })

    db.commit()

    return {"children": children, "count": len(children)}


def _get_canvas_size(project_id: str) -> dict:
    manifest_path = Path(settings.storage_path) / "outputs" / project_id / "layers" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        cs = manifest.get("canvas_size", {})
        return {"width": cs.get("width", 400), "height": cs.get("height", 700)}
    return {"width": 400, "height": 700}
