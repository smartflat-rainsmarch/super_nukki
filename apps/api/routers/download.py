from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(prefix="/api", tags=["download"])


@router.get("/download/{project_id}")
async def download_psd(project_id: str, db: Session = Depends(get_db)):
    return {"message": "Download endpoint ready", "project_id": project_id}
