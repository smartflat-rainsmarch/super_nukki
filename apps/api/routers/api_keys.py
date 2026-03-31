"""API key management for enterprise/pro programmatic access."""
import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import require_auth
from database import get_db
from models import User

router = APIRouter(prefix="/api/keys", tags=["api-keys"])

# In-memory store (production: DB table)
_api_keys: dict[str, dict] = {}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class CreateKeyRequest(BaseModel):
    name: str
    rate_limit_per_minute: int = 60


class CreateKeyResponse(BaseModel):
    key_id: str
    api_key: str  # only shown once
    name: str
    rate_limit_per_minute: int


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def authenticate_api_key(
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> User | None:
    if not api_key:
        return None

    key_hash = _hash_key(api_key)
    key_data = _api_keys.get(key_hash)
    if not key_data:
        return None

    user = db.query(User).filter(User.id == key_data["user_id"]).first()
    return user


@router.post("", response_model=CreateKeyResponse)
async def create_api_key(
    body: CreateKeyRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if user.plan_type != "pro":
        raise HTTPException(status_code=403, detail="API keys require Pro plan")

    raw_key = f"ui2psd_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    key_id = secrets.token_hex(8)

    _api_keys[key_hash] = {
        "key_id": key_id,
        "user_id": str(user.id),
        "name": body.name,
        "rate_limit_per_minute": body.rate_limit_per_minute,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return CreateKeyResponse(
        key_id=key_id,
        api_key=raw_key,
        name=body.name,
        rate_limit_per_minute=body.rate_limit_per_minute,
    )


@router.get("")
async def list_api_keys(user: User = Depends(require_auth)):
    user_keys = [
        {
            "key_id": v["key_id"],
            "name": v["name"],
            "rate_limit_per_minute": v["rate_limit_per_minute"],
            "created_at": v["created_at"],
        }
        for v in _api_keys.values()
        if v["user_id"] == str(user.id)
    ]
    return {"keys": user_keys}


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    user: User = Depends(require_auth),
):
    to_remove = None
    for k_hash, v in _api_keys.items():
        if v["key_id"] == key_id and v["user_id"] == str(user.id):
            to_remove = k_hash
            break

    if not to_remove:
        raise HTTPException(status_code=404, detail="API key not found")

    del _api_keys[to_remove]
    return {"status": "revoked", "key_id": key_id}
