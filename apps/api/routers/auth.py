from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, require_auth, verify_password
from database import get_db
from models import Billing, User
from oauth import (
    OAuthUserInfo,
    exchange_google_code,
    exchange_kakao_code,
    get_google_auth_url,
    get_kakao_auth_url,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthCallbackRequest(BaseModel):
    code: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    plan_type: str
    name: str | None = None
    profile_image: str | None = None
    auth_provider: str = "email"


class UserResponse(BaseModel):
    id: str
    email: str
    plan_type: str
    name: str | None = None
    profile_image: str | None = None
    auth_provider: str = "email"


def _build_auth_response(user: User, token: str) -> AuthResponse:
    return AuthResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        plan_type=user.plan_type,
        name=user.name,
        profile_image=user.profile_image,
        auth_provider=user.auth_provider,
    )


def _find_or_create_oauth_user(info: OAuthUserInfo, db: Session) -> User:
    user = db.query(User).filter(User.email == info.email).first()

    if user:
        user.auth_provider = info.provider
        user.provider_id = info.provider_id
        if info.name and not user.name:
            user.name = info.name
        if info.profile_image and not user.profile_image:
            user.profile_image = info.profile_image
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=info.email,
        password=None,
        plan_type="free",
        auth_provider=info.provider,
        provider_id=info.provider_id,
        name=info.name,
        profile_image=info.profile_image,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    billing = Billing(user_id=user.id, plan="free", usage_count=0)
    db.add(billing)
    db.commit()

    return user


# --- Email Auth ---

@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        if existing.auth_provider != "email":
            raise HTTPException(
                status_code=409,
                detail=f"이 이메일은 {existing.auth_provider}로 가입된 계정입니다. {existing.auth_provider}로 로그인해주세요.",
            )
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        password=hash_password(body.password),
        plan_type="free",
        auth_provider="email",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    billing = Billing(user_id=user.id, plan="free", usage_count=0)
    db.add(billing)
    db.commit()

    token = create_access_token(str(user.id))
    return _build_auth_response(user, token)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.auth_provider != "email" and not user.password:
        raise HTTPException(
            status_code=401,
            detail=f"이 계정은 {user.auth_provider}로 가입되었습니다. {user.auth_provider}로 로그인해주세요.",
        )

    if not user.password or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(str(user.id))
    return _build_auth_response(user, token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_auth)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        plan_type=user.plan_type,
        name=user.name,
        profile_image=user.profile_image,
        auth_provider=user.auth_provider,
    )


# --- Google OAuth ---

@router.get("/google/url")
async def google_login_url():
    return {"url": get_google_auth_url()}


@router.post("/google/callback", response_model=AuthResponse)
async def google_callback(body: OAuthCallbackRequest, db: Session = Depends(get_db)):
    try:
        info = await exchange_google_code(body.code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google 인증 실패: {str(e)}")

    user = _find_or_create_oauth_user(info, db)
    token = create_access_token(str(user.id))
    return _build_auth_response(user, token)


# --- Kakao OAuth ---

@router.get("/kakao/url")
async def kakao_login_url():
    return {"url": get_kakao_auth_url()}


@router.post("/kakao/callback", response_model=AuthResponse)
async def kakao_callback(body: OAuthCallbackRequest, db: Session = Depends(get_db)):
    try:
        info = await exchange_kakao_code(body.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"카카오 인증 실패: {str(e)}")

    user = _find_or_create_oauth_user(info, db)
    token = create_access_token(str(user.id))
    return _build_auth_response(user, token)
