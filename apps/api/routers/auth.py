import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth import SECRET_KEY, ALGORITHM, create_access_token, hash_password, require_auth, verify_password
from database import get_db
from email_sender import send_verification_email
from models import Billing, EmailVerification, User
from oauth import (
    OAuthUserInfo,
    exchange_google_code,
    exchange_kakao_code,
    get_google_auth_url,
    get_kakao_auth_url,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

VERIFY_CODE_EXPIRE_MINUTES = 5
VERIFY_TOKEN_EXPIRE_MINUTES = 10
MAX_VERIFY_ATTEMPTS = 5


class SendCodeRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    verified_token: str | None = None


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


# --- Email Verification ---

@router.post("/send-code")
async def send_code(body: SendCodeRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        if existing.auth_provider != "email":
            raise HTTPException(status_code=409, detail=f"이 이메일은 {existing.auth_provider}로 가입된 계정입니다.")
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.")

    recent = (
        db.query(EmailVerification)
        .filter(EmailVerification.email == body.email)
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    if recent and (now - recent.created_at).total_seconds() < 60:
        raise HTTPException(status_code=429, detail="인증번호를 너무 자주 요청했습니다. 60초 후 다시 시도하세요.")

    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = now + timedelta(minutes=VERIFY_CODE_EXPIRE_MINUTES)

    verification = EmailVerification(
        email=body.email,
        code=code,
        expires_at=expires_at,
    )
    db.add(verification)
    db.commit()

    sent = send_verification_email(body.email, code)

    response = {"message": "인증번호가 발송되었습니다.", "expires_in": VERIFY_CODE_EXPIRE_MINUTES * 60}
    if not sent:
        response["dev_code"] = code
    return response


@router.post("/verify-code")
async def verify_code(body: VerifyCodeRequest, db: Session = Depends(get_db)):
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.email == body.email,
            EmailVerification.verified == 0,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if not verification:
        raise HTTPException(status_code=400, detail="인증번호를 먼저 요청하세요.")

    if verification.attempts >= MAX_VERIFY_ATTEMPTS:
        raise HTTPException(status_code=429, detail="너무 많은 시도입니다. 인증번호를 다시 요청하세요.")

    now = datetime.now(timezone.utc)
    if now > verification.expires_at:
        raise HTTPException(status_code=400, detail="인증번호가 만료되었습니다. 다시 요청하세요.")

    if verification.code != body.code:
        verification.attempts = verification.attempts + 1
        db.commit()
        remaining = MAX_VERIFY_ATTEMPTS - verification.attempts
        raise HTTPException(status_code=400, detail=f"인증번호가 일치하지 않습니다. (남은 시도: {remaining}회)")

    verification.verified = 1
    db.commit()

    verified_token = jwt.encode(
        {"sub": body.email, "purpose": "email_verify", "exp": now + timedelta(minutes=VERIFY_TOKEN_EXPIRE_MINUTES)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return {"message": "인증 완료", "verified_token": verified_token}


# --- Email Auth ---

@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    if body.verified_token:
        try:
            payload = jwt.decode(body.verified_token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("purpose") != "email_verify" or payload.get("sub") != body.email:
                raise HTTPException(status_code=400, detail="유효하지 않은 인증 토큰입니다.")
        except Exception:
            raise HTTPException(status_code=400, detail="인증 토큰이 만료되었거나 유효하지 않습니다.")

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
