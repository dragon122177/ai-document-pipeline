from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import Role
from .security import TokenError, decode_token
from .services import Services


bearer = HTTPBearer(auto_error=False)


def get_services(request: Request) -> Services:
    return request.app.state.services


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer)
    ],
    services: Annotated[Services, Depends(get_services)],
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        )
    try:
        claims = decode_token(
            credentials.credentials, services.settings.token_secret
        )
    except TokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error
    user = services.database.fetch_one(
        "SELECT id,email,name,role FROM users WHERE id = ?",
        (claims.get("sub"),),
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user_not_found",
        )
    return user


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
AppServices = Annotated[Services, Depends(get_services)]


def require_roles(*roles: Role) -> Callable[..., dict[str, Any]]:
    allowed = {role.value for role in roles}

    def permission_dependency(
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        if current_user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient_permissions",
            )
        return current_user

    return permission_dependency
