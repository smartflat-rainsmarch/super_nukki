"""OAuth 2.0 utilities for Google and Kakao login."""
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from config import settings


@dataclass(frozen=True)
class OAuthUserInfo:
    email: str
    name: str | None
    profile_image: str | None
    provider: str  # "google" | "kakao"
    provider_id: str


# --- Google ---

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def get_google_auth_url() -> str:
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_code(code: str) -> OAuthUserInfo:
    if not settings.google_client_id:
        return _mock_google_user(code)

    async with httpx.AsyncClient() as client:
        token_res = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        })
        token_res.raise_for_status()
        access_token = token_res.json()["access_token"]

        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_res.raise_for_status()
        data = user_res.json()

    return OAuthUserInfo(
        email=data["email"],
        name=data.get("name"),
        profile_image=data.get("picture"),
        provider="google",
        provider_id=data["id"],
    )


# --- Kakao ---

KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"


def get_kakao_auth_url() -> str:
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.kakao_client_id,
        "redirect_uri": settings.kakao_redirect_uri,
        "response_type": "code",
        "scope": "account_email profile_nickname profile_image",
        "state": state,
    }
    return f"{KAKAO_AUTH_URL}?{urlencode(params)}"


async def exchange_kakao_code(code: str) -> OAuthUserInfo:
    if not settings.kakao_client_id:
        return _mock_kakao_user(code)

    async with httpx.AsyncClient() as client:
        token_res = await client.post(KAKAO_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": settings.kakao_client_id,
            "client_secret": settings.kakao_client_secret,
            "redirect_uri": settings.kakao_redirect_uri,
            "code": code,
        })
        token_res.raise_for_status()
        access_token = token_res.json()["access_token"]

        user_res = await client.get(
            KAKAO_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_res.raise_for_status()
        data = user_res.json()

    kakao_account = data.get("kakao_account", {})
    profile = kakao_account.get("profile", {})
    email = kakao_account.get("email")

    if not email:
        raise ValueError("이메일 동의가 필요합니다. 카카오 로그인 시 이메일 제공에 동의해주세요.")

    return OAuthUserInfo(
        email=email,
        name=profile.get("nickname"),
        profile_image=profile.get("profile_image_url"),
        provider="kakao",
        provider_id=str(data["id"]),
    )


# --- Mock (개발용, OAuth 키 미설정 시 사용) ---

def _mock_google_user(code: str) -> OAuthUserInfo:
    return OAuthUserInfo(
        email=f"google-{code[:8]}@mock.ui2psd.com",
        name="Google Mock User",
        profile_image=None,
        provider="google",
        provider_id=f"google-mock-{code[:8]}",
    )


def _mock_kakao_user(code: str) -> OAuthUserInfo:
    return OAuthUserInfo(
        email=f"kakao-{code[:8]}@mock.ui2psd.com",
        name="카카오 Mock User",
        profile_image=None,
        provider="kakao",
        provider_id=f"kakao-mock-{code[:8]}",
    )
