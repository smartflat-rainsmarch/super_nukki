from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(prefix="/api", tags=["usage"])


@router.get("/usage")
async def get_usage(db: Session = Depends(get_db)):
    return {"remaining": 3, "plan": "free", "total": 3}
