import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import FigmaShare, Project, User

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
        formats.extend(["png_zip", "figma_json", "figma_share"])

    if user.plan_type == "pro":
        formats.extend(["react", "design_tokens", "component_schema"])

    return {
        "project_id": project_id,
        "available_formats": formats,
        "plan": user.plan_type,
    }


@router.post("/{project_id}/figma-share")
async def create_figma_share(
    project_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.user_id and str(project.user_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    if project.status != "done":
        raise HTTPException(status_code=400, detail="Project not complete")

    share_code = secrets.token_urlsafe(16)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    share = FigmaShare(
        project_id=project_id,
        share_code=share_code,
        expires_at=expires_at,
    )
    db.add(share)
    db.commit()

    return {
        "share_code": share_code,
        "share_url": f"/api/share/{share_code}",
        "expires_in": 3600,
    }
