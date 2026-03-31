from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(prefix="/api", tags=["project"])


@router.get("/project/{project_id}")
async def get_project(project_id: str, db: Session = Depends(get_db)):
    return {"project_id": project_id, "status": "pending"}


@router.get("/project/{project_id}/result")
async def get_project_result(project_id: str, db: Session = Depends(get_db)):
    return {"project_id": project_id, "layers": [], "psd_url": None}
