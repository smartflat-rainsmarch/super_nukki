"""Custom model configuration for enterprise customers."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import User

router = APIRouter(prefix="/api/model-config", tags=["model-config"])

# Default engine parameters
DEFAULT_CONFIG = {
    "ocr_engine": "paddleocr",
    "ocr_languages": ["ko", "en"],
    "segmentation_model": "opencv_contour",
    "inpainting_method": "telea",
    "inpainting_radius": 5,
    "max_resolution": 2048,
    "enable_ensemble_ocr": False,
    "enable_adaptive_inpaint": False,
    "enable_multipass": False,
    "confidence_threshold": 0.5,
}


class ModelConfigUpdate(BaseModel):
    ocr_engine: str | None = None
    ocr_languages: list[str] | None = None
    segmentation_model: str | None = None
    inpainting_method: str | None = None
    inpainting_radius: int | None = None
    max_resolution: int | None = None
    enable_ensemble_ocr: bool | None = None
    enable_adaptive_inpaint: bool | None = None
    enable_multipass: bool | None = None
    confidence_threshold: float | None = None


# In-memory config store (in production: persisted per-team)
_team_configs: dict[str, dict] = {}


@router.get("/defaults")
async def get_defaults(user: User = Depends(require_auth)):
    return {"config": DEFAULT_CONFIG}


@router.get("/{team_id}")
async def get_team_config(
    team_id: str,
    user: User = Depends(require_auth),
):
    config = {**DEFAULT_CONFIG, **_team_configs.get(team_id, {})}
    return {"team_id": team_id, "config": config}


@router.put("/{team_id}")
async def update_team_config(
    team_id: str,
    body: ModelConfigUpdate,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if user.plan_type != "pro":
        raise HTTPException(status_code=403, detail="Custom model config requires Pro plan")

    updates = body.model_dump(exclude_none=True)

    if "inpainting_radius" in updates:
        if not (1 <= updates["inpainting_radius"] <= 20):
            raise HTTPException(status_code=400, detail="inpainting_radius must be 1-20")

    if "max_resolution" in updates:
        if not (512 <= updates["max_resolution"] <= 4096):
            raise HTTPException(status_code=400, detail="max_resolution must be 512-4096")

    if "confidence_threshold" in updates:
        if not (0.0 <= updates["confidence_threshold"] <= 1.0):
            raise HTTPException(status_code=400, detail="confidence_threshold must be 0.0-1.0")

    existing = _team_configs.get(team_id, {})
    _team_configs[team_id] = {**existing, **updates}

    return {
        "team_id": team_id,
        "config": {**DEFAULT_CONFIG, **_team_configs[team_id]},
        "updated_fields": list(updates.keys()),
    }


@router.get("/{team_id}/versions")
async def list_model_versions(
    team_id: str,
    user: User = Depends(require_auth),
):
    return {
        "team_id": team_id,
        "versions": [
            {"version": "v1.0", "status": "active", "engine": "opencv+paddleocr"},
            {"version": "v1.1-beta", "status": "available", "engine": "opencv+paddleocr+lama"},
        ],
    }
