from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..audit import write_audit
from ..dependencies import AppServices, CurrentUser
from ..models import LoginRequest, SessionResponse, UserPublic
from ..security import create_token, verify_password


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, services: AppServices) -> dict[str, object]:
    user = services.database.fetch_one(
        """
        SELECT id,email,name,role,password_hash
        FROM users
        WHERE lower(email) = lower(?)
        """,
        (payload.email.strip(),),
    )
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        )
    token = create_token(
        {"sub": user["id"], "role": user["role"]},
        services.settings.token_secret,
        services.settings.token_ttl_minutes,
    )
    write_audit(
        services.database,
        user["id"],
        "USER_LOGIN",
        "user",
        user["id"],
    )
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
        },
    }


@router.get("/me", response_model=UserPublic)
def me(current_user: CurrentUser) -> dict[str, str]:
    return current_user
