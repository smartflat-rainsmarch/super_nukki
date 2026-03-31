from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user, require_auth
from database import get_db
from models import Billing, User

router = APIRouter(prefix="/api", tags=["usage"])

PLAN_LIMITS = {
    "free": 3,
    "basic": 100,
    "pro": 500,
}


def check_usage_limit(user: User, db: Session) -> bool:
    billing = db.query(Billing).filter(Billing.user_id == user.id).first()
    if not billing:
        return False

    now = datetime.now(timezone.utc)
    if billing.reset_date and now >= billing.reset_date:
        billing.usage_count = 0
        next_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            next_month = next_month.replace(year=now.year + 1, month=1)
        else:
            next_month = next_month.replace(month=now.month + 1)
        billing.reset_date = next_month
        db.commit()

    limit = PLAN_LIMITS.get(billing.plan, 3)
    return billing.usage_count < limit


def increment_usage(user: User, db: Session):
    billing = db.query(Billing).filter(Billing.user_id == user.id).first()
    if billing:
        billing.usage_count = billing.usage_count + 1
        db.commit()


@router.get("/usage")
async def get_usage(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    billing = db.query(Billing).filter(Billing.user_id == user.id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing record not found")

    limit = PLAN_LIMITS.get(billing.plan, 3)
    remaining = max(0, limit - billing.usage_count)

    return {
        "plan": billing.plan,
        "usage_count": billing.usage_count,
        "limit": limit,
        "remaining": remaining,
        "reset_date": billing.reset_date.isoformat() if billing.reset_date else None,
    }
