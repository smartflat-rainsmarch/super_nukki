from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import Project, User

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    query = db.query(Project).filter(Project.user_id == user.id)
    total = query.count()
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "projects": [
            {
                "id": str(p.id),
                "image_url": p.image_url,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ],
    }


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user.id,
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return {"status": "deleted", "id": project_id}
