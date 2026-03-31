from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import Billing, Job, Project, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(user: User = Depends(require_auth)):
    # MVP: check plan_type == "pro" as admin proxy
    # TODO: add is_admin column to User model
    if user.plan_type != "pro":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/stats")
async def get_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    completed_jobs = db.query(func.count(Job.id)).filter(Job.status == "completed").scalar() or 0
    failed_jobs = db.query(func.count(Job.id)).filter(Job.status == "failed").scalar() or 0
    total_jobs = db.query(func.count(Job.id)).scalar() or 0

    success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

    plan_counts = (
        db.query(Billing.plan, func.count(Billing.id))
        .group_by(Billing.plan)
        .all()
    )

    return {
        "users": {
            "total": total_users,
            "by_plan": {plan: count for plan, count in plan_counts},
        },
        "projects": {
            "total": total_projects,
        },
        "jobs": {
            "total": total_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs,
            "success_rate": round(success_rate, 1),
        },
    }


@router.get("/users")
async def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(func.count(User.id)).scalar() or 0

    return {
        "total": total,
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "plan_type": u.plan_type,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.get("/jobs")
async def list_jobs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    query = db.query(Job)
    if status_filter:
        query = query.filter(Job.status == status_filter)

    jobs = query.order_by(Job.id.desc()).offset(skip).limit(limit).all()
    total = query.count()

    return {
        "total": total,
        "jobs": [
            {
                "id": str(j.id),
                "project_id": str(j.project_id),
                "status": j.status,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            }
            for j in jobs
        ],
    }
