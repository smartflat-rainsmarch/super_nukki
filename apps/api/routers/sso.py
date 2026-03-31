"""SSO (SAML/OIDC) integration endpoints for enterprise customers."""
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, require_auth
from database import get_db
from models import Billing, Team, TeamMember, User

router = APIRouter(prefix="/api/sso", tags=["sso"])


class SSOConfig(BaseModel):
    provider: str  # saml, oidc
    entity_id: str | None = None
    sso_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    issuer: str | None = None
    team_id: str


class SSOCallbackData(BaseModel):
    email: str
    name: str | None = None
    provider: str
    team_id: str


@router.post("/configure")
async def configure_sso(
    body: SSOConfig,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.id == body.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if str(team.owner_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Only team owner can configure SSO")

    # In production: store SSO config in a dedicated table
    # For MVP: return confirmation
    return {
        "status": "configured",
        "provider": body.provider,
        "team_id": body.team_id,
        "sso_login_url": f"/api/sso/login/{body.team_id}",
    }


@router.post("/callback")
async def sso_callback(
    body: SSOCallbackData,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == body.email).first()

    if not user:
        user = User(
            email=body.email,
            password=hash_password(f"sso-{body.provider}-{body.email}"),
            plan_type="pro",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        billing = Billing(user_id=user.id, plan="pro", usage_count=0)
        db.add(billing)
        db.commit()

    existing_member = db.query(TeamMember).filter(
        TeamMember.team_id == body.team_id,
        TeamMember.user_id == user.id,
    ).first()

    if not existing_member:
        member = TeamMember(team_id=body.team_id, user_id=user.id, role="member")
        db.add(member)
        db.commit()

    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer"}
