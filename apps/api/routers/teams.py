from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import Team, TeamMember, User

router = APIRouter(prefix="/api/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    name: str


class InviteRequest(BaseModel):
    email: EmailStr


@router.post("")
async def create_team(
    body: CreateTeamRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    team = Team(name=body.name, owner_id=user.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    member = TeamMember(team_id=team.id, user_id=user.id, role="owner")
    db.add(member)
    db.commit()

    return {"id": str(team.id), "name": team.name}


@router.get("")
async def list_teams(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    memberships = db.query(TeamMember).filter(TeamMember.user_id == user.id).all()
    team_ids = [m.team_id for m in memberships]
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all() if team_ids else []

    return {
        "teams": [
            {
                "id": str(t.id),
                "name": t.name,
                "role": next(
                    (m.role for m in memberships if m.team_id == t.id), "member"
                ),
                "member_count": db.query(TeamMember).filter(TeamMember.team_id == t.id).count(),
            }
            for t in teams
        ]
    }


@router.post("/{team_id}/invite")
async def invite_member(
    team_id: str,
    body: InviteRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user.id,
        TeamMember.role.in_(["owner", "admin"]),
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Only owners/admins can invite")

    invited_user = db.query(User).filter(User.email == body.email).first()
    if not invited_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == invited_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already a member")

    new_member = TeamMember(
        team_id=team_id,
        user_id=invited_user.id,
        role="member",
    )
    db.add(new_member)
    db.commit()

    return {"status": "invited", "email": body.email}


@router.get("/{team_id}/members")
async def list_members(
    team_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a team member")

    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    result = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u:
            result.append({
                "user_id": str(u.id),
                "email": u.email,
                "role": m.role,
            })

    return {"members": result}
