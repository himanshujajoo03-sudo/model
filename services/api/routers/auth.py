"""
Auth router — POST /auth/login
Per 04_API_CONTRACT.md §3.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from pydantic import BaseModel

from config import settings

router = APIRouter(tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Authenticate the configured admin and issue a JWT."""
    print(f"DEBUG: Received username={repr(req.username)}, password={repr(req.password)}")
    print(f"DEBUG: Config admin_username={repr(settings.admin_username)}, admin_password={repr(settings.admin_password)}")
    print(f"DEBUG: Username match: {req.username == settings.admin_username}")
    print(f"DEBUG: Password match: {req.password == settings.admin_password}")
    
    # Direct string comparison (plain text)
    username_ok = (req.username == settings.admin_username)
    password_ok = (req.password == settings.admin_password)
    
    print(f"DEBUG: username_ok={username_ok}, password_ok={password_ok}")
    
    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")
    
    if not settings.jwt_secret_key:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY is not configured")

    expires_in = settings.jwt_expiration_hours * 3600
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": settings.admin_username,
            "role": "admin",
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    print(f"DEBUG: Login successful, token created")
    return LoginResponse(access_token=token, expires_in=expires_in)


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    """Validate the JWT and require the admin role."""
    if not settings.jwt_secret_key:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY is not configured")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=["HS256"])
        if payload.get("sub") != settings.admin_username or payload.get("role") != "admin":
            raise ValueError("not admin")
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")
