from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, require_auth, verify_password
from database import get_db
from models import Billing, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    plan_type: str


class UserResponse(BaseModel):
    id: str
    email: str
    plan_type: str


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        password=hash_password(body.password),
        plan_type="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    billing = Billing(user_id=user.id, plan="free", usage_count=0)
    db.add(billing)
    db.commit()

    token = create_access_token(str(user.id))

    return AuthResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        plan_type=user.plan_type,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(str(user.id))

    return AuthResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        plan_type=user.plan_type,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_auth)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        plan_type=user.plan_type,
    )
