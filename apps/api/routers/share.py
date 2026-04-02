"""Public share endpoint for Figma Plugin to fetch layer data."""
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import FigmaShare, Layer, Project

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/{share_code}")
async def get_shared_data(share_code: str, db: Session = Depends(get_db)):
    share = db.query(FigmaShare).filter(FigmaShare.share_code == share_code).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share link not found")

    now = datetime.now(timezone.utc)
    exp = share.expires_at
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        raise HTTPException(status_code=410, detail="Share link expired")

    project = db.query(Project).filter(Project.id == share.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    layers = db.query(Layer).filter(
        Layer.project_id == share.project_id
    ).order_by(Layer.z_index).all()

    # Read canvas size from manifest
    manifest_path = (
        Path(settings.storage_path) / "outputs" / str(share.project_id) / "layers" / "manifest.json"
    )
    canvas_size = {"width": 400, "height": 700}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        cs = manifest.get("canvas_size", {})
        canvas_size = {"width": cs.get("width", 400), "height": cs.get("height", 700)}

    return {
        "project_id": str(share.project_id),
        "canvas_size": canvas_size,
        "layers": [
            {
                "type": l.type,
                "position": l.position,
                "image_url": l.image_url,
                "text_content": l.text_content,
                "z_index": l.z_index,
            }
            for l in layers
        ],
    }
