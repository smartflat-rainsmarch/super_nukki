"""Role-Based Access Control for team resources."""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import TeamMember, User

ROLE_HIERARCHY = {"owner": 3, "admin": 2, "member": 1}


def get_team_role(user_id: str, team_id: str, db: Session) -> str | None:
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id,
    ).first()
    return membership.role if membership else None


def require_team_role(team_id: str, min_role: str = "member"):
    def checker(
        user: User = Depends(require_auth),
        db: Session = Depends(get_db),
    ) -> User:
        role = get_team_role(str(user.id), team_id, db)
        if role is None:
            raise HTTPException(status_code=403, detail="Not a team member")

        if ROLE_HIERARCHY.get(role, 0) < ROLE_HIERARCHY.get(min_role, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Requires {min_role} role or higher",
            )
        return user

    return checker


def check_permission(user_id: str, team_id: str, min_role: str, db: Session) -> bool:
    role = get_team_role(user_id, team_id, db)
    if role is None:
        return False
    return ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(min_role, 0)
