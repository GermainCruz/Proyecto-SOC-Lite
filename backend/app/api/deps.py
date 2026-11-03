"""Dependencias de autenticación y autorización (RBAC)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Annotated, Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models import Permission, RolePermission, User
from app.db.session import get_session

bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class CurrentUser:
    id: uuid.UUID
    email: str
    role_code: str
    role_name: str
    area: str | None
    permissions: set[str] = field(default_factory=set)

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    @property
    def is_admin(self) -> bool:
        return self.role_code == "admin"


async def _load_permissions(session: AsyncSession, role_id: int) -> set[str]:
    rows = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    return set(rows.scalars().all())


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    # El rol del token puede haber cambiado: siempre se revalida contra la BD
    if payload.get("role") != user.role.code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Los permisos cambiaron; vuelva a iniciar sesión",
        )

    current = CurrentUser(
        id=user.id,
        email=str(user.email),
        role_code=user.role.code,
        role_name=user.role.name,
        area=user.area,
        permissions=await _load_permissions(session, user.role_id),
    )
    request.state.current_user = current
    return current


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require(*permissions: str, mode: str = "all") -> Callable:
    """Fábrica de dependencias: exige uno o varios permisos RBAC.

    Uso: @router.get("/", dependencies=[Depends(require("alerts:read"))])
    """
    if mode not in {"all", "any"}:
        raise ValueError("mode debe ser 'all' o 'any'")

    async def _checker(user: CurrentUserDep) -> CurrentUser:
        granted = {p: user.can(p) for p in permissions}
        allowed = all(granted.values()) if mode == "all" else any(granted.values())
        if not allowed:
            missing = [p for p, ok in granted.items() if not ok]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Permisos insuficientes",
                    "missing": missing,
                    "role": user.role_code,
                },
            )
        return user

    return _checker


def client_context(request: Request) -> dict[str, str | None]:
    """IP real (respetando proxy) y user-agent para la bitácora."""
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    return {"ip": ip, "user_agent": request.headers.get("user-agent")}
