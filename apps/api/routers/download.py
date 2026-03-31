from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import Project

router = APIRouter(prefix="/api", tags=["download"])


@router.get("/download/{project_id}")
async def download_psd(project_id: str, db: Session = Depends(get_db)):
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != "done":
        raise HTTPException(status_code=400, detail="Project processing not complete")

    psd_path = Path(settings.storage_path) / "outputs" / project_id / "output.psd"
    if not psd_path.exists():
        raise HTTPException(status_code=404, detail="PSD file not found")

    return FileResponse(
        path=str(psd_path),
        media_type="application/octet-stream",
        filename=f"ui2psd_{project_id}.psd",
    )
