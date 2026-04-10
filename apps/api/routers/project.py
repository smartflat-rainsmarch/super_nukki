import json
import time
import uuid
from pathlib import Path
from uuid import UUID

import cv2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from config import settings
from database import get_db
from models import Job, Layer, Project, User


class BatchRemoveRequest(BaseModel):
    layer_ids: list[str]

    @field_validator("layer_ids")
    @classmethod
    def validate_layer_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("layer_ids must be non-empty")
        if len(v) > 20:
            raise ValueError("Maximum 20 layers per batch")
        for lid in v:
            try:
                UUID(lid)
            except ValueError:
                raise ValueError(f"Invalid layer ID: {lid}")
        return v

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


@router.post("/project/{project_id}/layer/{layer_id}/remove")
async def remove_element(
    project_id: str,
    layer_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    try:
        UUID(layer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid layer ID")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id and (user is None or str(user.id) != str(project.user_id)):
        raise HTTPException(status_code=403, detail="Forbidden")

    layer = db.query(Layer).filter(
        Layer.id == layer_id, Layer.project_id == project_id,
    ).first()
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    if layer.type == "background":
        raise HTTPException(status_code=400, detail="Cannot remove background layer")

    if not layer.position:
        raise HTTPException(status_code=400, detail="Layer has no position data")

    bg_layer = db.query(Layer).filter(
        Layer.project_id == project_id,
        Layer.type == "background",
        Layer.parent_id == layer.parent_id,
    ).first()
    if not bg_layer or not bg_layer.image_url:
        raise HTTPException(status_code=400, detail="Background layer not found")

    url_path = bg_layer.image_url.replace("/storage/", "", 1) if bg_layer.image_url.startswith("/storage/") else bg_layer.image_url
    bg_image_path = (Path(settings.storage_path) / url_path).resolve()
    storage_root = Path(settings.storage_path).resolve()
    if not str(bg_image_path).startswith(str(storage_root)):
        raise HTTPException(status_code=400, detail="Invalid background path")
    if not bg_image_path.exists():
        raise HTTPException(status_code=404, detail="Background image file not found")

    bg_image = cv2.imread(str(bg_image_path))
    if bg_image is None:
        raise HTTPException(status_code=500, detail="Failed to load background image")

    pos = layer.position
    bbox = (pos.get("x", 0), pos.get("y", 0), pos.get("w", 0), pos.get("h", 0))

    if bbox[2] <= 0 or bbox[3] <= 0:
        raise HTTPException(status_code=400, detail="Layer has invalid dimensions")

    from engine.inpainting_advanced import inpaint_element_removal
    result, warning = inpaint_element_removal(bg_image, bbox)

    timestamp = int(time.time() * 1000)
    new_bg_filename = f"background_{timestamp}.png"
    new_bg_path = bg_image_path.parent / new_bg_filename
    cv2.imwrite(str(new_bg_path), result.restored_image)

    url_dir = "/".join(bg_layer.image_url.rsplit("/", 1)[:-1])
    new_image_url = f"{url_dir}/{new_bg_filename}"
    bg_layer.image_url = new_image_url

    def _delete_layer_tree(parent_id: str) -> None:
        children = db.query(Layer).filter(Layer.parent_id == parent_id).all()
        for child in children:
            _delete_layer_tree(str(child.id))
            db.delete(child)

    _delete_layer_tree(str(layer.id))
    db.delete(layer)
    db.commit()

    return {
        "success": True,
        "background_url": new_image_url,
        "quality_score": result.quality_score,
        "warning": warning,
    }


@router.post("/project/{project_id}/layers/remove-batch")
async def remove_elements_batch(
    project_id: str,
    body: BatchRemoveRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id and (user is None or str(user.id) != str(project.user_id)):
        raise HTTPException(status_code=403, detail="Forbidden")

    from engine.inpainting_advanced import inpaint_element_removal

    def _delete_tree(parent_id: str) -> None:
        children = db.query(Layer).filter(Layer.parent_id == parent_id).all()
        for child in children:
            _delete_tree(str(child.id))
            db.delete(child)

    # Validate all layers first before processing
    layers_to_remove = []
    first_parent_id = None

    for lid in body.layer_ids:
        layer = db.query(Layer).filter(
            Layer.id == lid, Layer.project_id == project_id,
        ).first()
        if not layer:
            raise HTTPException(status_code=404, detail=f"Layer {lid} not found")
        if layer.type == "background":
            raise HTTPException(status_code=400, detail="Cannot remove background layer")
        if not layer.position:
            raise HTTPException(status_code=400, detail=f"Layer {lid} has no position data")

        pos = layer.position
        bbox = (pos.get("x", 0), pos.get("y", 0), pos.get("w", 0), pos.get("h", 0))
        if bbox[2] <= 0 or bbox[3] <= 0:
            raise HTTPException(status_code=400, detail=f"Layer {lid} has invalid dimensions")

        if first_parent_id is None:
            first_parent_id = layer.parent_id
        elif layer.parent_id != first_parent_id:
            raise HTTPException(
                status_code=400,
                detail="All layers must belong to the same parent group",
            )

        layers_to_remove.append((layer, bbox))

    # Load background
    bg_layer = db.query(Layer).filter(
        Layer.project_id == project_id,
        Layer.type == "background",
        Layer.parent_id == first_parent_id,
    ).first()
    if not bg_layer or not bg_layer.image_url:
        raise HTTPException(status_code=400, detail="Background layer not found")

    url_path = bg_layer.image_url.replace("/storage/", "", 1) if bg_layer.image_url.startswith("/storage/") else bg_layer.image_url
    bg_image_path = (Path(settings.storage_path) / url_path).resolve()
    storage_root = Path(settings.storage_path).resolve()
    if not str(bg_image_path).startswith(str(storage_root)):
        raise HTTPException(status_code=400, detail="Invalid background path")
    if not bg_image_path.exists():
        raise HTTPException(status_code=404, detail="Background image file not found")

    bg_image = cv2.imread(str(bg_image_path))
    if bg_image is None:
        raise HTTPException(status_code=500, detail="Failed to load background image")

    # Process removals sequentially
    results = []
    try:
        for layer, bbox in layers_to_remove:
            result, warning = inpaint_element_removal(bg_image, bbox)
            bg_image = result.restored_image

            results.append({
                "layer_id": str(layer.id),
                "quality_score": result.quality_score,
                "warning": warning,
            })

            _delete_tree(str(layer.id))
            db.delete(layer)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Batch removal failed, changes rolled back")

    timestamp = int(time.time() * 1000)
    new_bg_filename = f"background_{timestamp}.png"
    new_bg_path = bg_image_path.parent / new_bg_filename
    cv2.imwrite(str(new_bg_path), bg_image)

    url_dir = "/".join(bg_layer.image_url.rsplit("/", 1)[:-1])
    new_image_url = f"{url_dir}/{new_bg_filename}"
    bg_layer.image_url = new_image_url

    db.commit()

    return {
        "success": True,
        "results": results,
        "background_url": new_image_url,
    }


def _get_canvas_size(project_id: str) -> dict:
    manifest_path = Path(settings.storage_path) / "outputs" / project_id / "layers" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        cs = manifest.get("canvas_size", {})
        return {"width": cs.get("width", 400), "height": cs.get("height", 700)}
    return {"width": 400, "height": 700}
