"""SLA monitoring and system health endpoints."""
import time

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import Job, User

router = APIRouter(prefix="/api/sla", tags=["sla"])

_start_time = time.time()


@router.get("/health")
async def sla_health():
    uptime = time.time() - _start_time
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime),
        "version": "0.1.0",
    }


@router.get("/metrics")
async def sla_metrics(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    total_jobs = db.query(func.count(Job.id)).scalar() or 0
    completed = db.query(func.count(Job.id)).filter(Job.status == "completed").scalar() or 0
    failed = db.query(func.count(Job.id)).filter(Job.status == "failed").scalar() or 0

    success_rate = (completed / total_jobs * 100) if total_jobs > 0 else 100.0

    return {
        "jobs": {
            "total": total_jobs,
            "completed": completed,
            "failed": failed,
            "success_rate": round(success_rate, 2),
        },
        "sla": {
            "target_success_rate": 99.5,
            "target_avg_processing_time_seconds": 20,
            "status": "meeting" if success_rate >= 99.5 else "below_target",
        },
    }
