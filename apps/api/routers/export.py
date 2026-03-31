from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import Project, User

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/{project_id}/formats")
async def available_formats(
    project_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    formats = ["psd"]

    if user.plan_type in ("basic", "pro"):
        formats.extend(["png_zip", "figma_json"])

    if user.plan_type == "pro":
        formats.extend(["react", "design_tokens", "component_schema"])

    return {
        "project_id": project_id,
        "available_formats": formats,
        "plan": user.plan_type,
    }
