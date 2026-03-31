from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import Layer, Project, User

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
async def list_assets(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    asset_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    query = (
        db.query(Layer)
        .join(Project, Layer.project_id == Project.id)
        .filter(Project.user_id == user.id)
    )

    if asset_type:
        query = query.filter(Layer.type == asset_type)

    total = query.count()
    layers = query.order_by(Layer.id.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "assets": [
            {
                "id": str(l.id),
                "project_id": str(l.project_id),
                "type": l.type,
                "text_content": l.text_content,
                "image_url": l.image_url,
                "position": l.position,
                "z_index": l.z_index,
            }
            for l in layers
        ],
    }


@router.get("/stats")
async def asset_stats(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    type_counts = (
        db.query(Layer.type, func.count(Layer.id))
        .join(Project, Layer.project_id == Project.id)
        .filter(Project.user_id == user.id)
        .group_by(Layer.type)
        .all()
    )

    return {
        "by_type": {t: c for t, c in type_counts},
        "total": sum(c for _, c in type_counts),
    }


@router.get("/search")
async def search_assets(
    q: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    layers = (
        db.query(Layer)
        .join(Project, Layer.project_id == Project.id)
        .filter(
            Project.user_id == user.id,
            Layer.text_content.ilike(f"%{q}%"),
        )
        .limit(limit)
        .all()
    )

    return {
        "query": q,
        "results": [
            {
                "id": str(l.id),
                "project_id": str(l.project_id),
                "type": l.type,
                "text_content": l.text_content,
            }
            for l in layers
        ],
    }
