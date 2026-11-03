"""Gestión de usuarios, roles y permisos (RBAC)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, client_context, require
from app.core.security import hash_password, password_policy_errors
from app.db.models import Permission, Role, RolePermission, User
from app.db.session import get_session
from app.schemas import PermissionOut, RoleOut, UserCreate, UserOut, UserUpdate
from app.services import audit

router = APIRouter(prefix="/users", tags=["Usuarios y RBAC"])
roles_router = APIRouter(prefix="/roles", tags=["Usuarios y RBAC"])


@router.get("", response_model=list[UserOut], summary="Listar usuarios")
async def list_users(
    _: CurrentUser = Depends(require("users:read")),
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None, max_length=80),
    active: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.full_name.ilike(like)))
    if active is not None:
        stmt = stmt.where(User.is_active.is_(active))
    return list((await session.execute(stmt)).scalars().unique().all())


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
async def create_user(
    payload: UserCreate,
    request: Request,
    actor: CurrentUser = Depends(require("users:create")),
    session: AsyncSession = Depends(get_session),
) -> User:
    errors = password_policy_errors(payload.password)
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Contraseña débil", "errors": errors})

    if (await session.execute(select(User.id).where(User.email == payload.email))).first():
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    role = (await session.execute(select(Role).where(Role.code == payload.role_code))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=422, detail="Rol inexistente")

    # Un analista no puede crear administradores (evita escalada de privilegios)
    if role.code == "admin" and actor.role_code != "admin":
        raise HTTPException(status_code=403, detail="Solo un administrador puede crear administradores")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        role=role,
        area=payload.area,
        created_by=actor.id,
    )
    session.add(user)
    await session.flush()

    await audit.record(
        action="users.create", module="users", user=actor, entity="user", entity_id=user.id,
        ip_address=client_context(request)["ip"], user_agent=request.headers.get("user-agent"),
        detail={"email": str(payload.email), "role": role.code}, session=session,
    )
    await session.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut, summary="Actualizar usuario")
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    actor: CurrentUser = Depends(require("users:update")),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario inexistente")

    changes: dict[str, object] = {}
    if payload.full_name is not None:
        user.full_name = payload.full_name
        changes["full_name"] = payload.full_name
    if payload.area is not None:
        user.area = payload.area
        changes["area"] = payload.area
    if payload.role_code is not None:
        role = (await session.execute(select(Role).where(Role.code == payload.role_code))).scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=422, detail="Rol inexistente")
        if role.code == "admin" and actor.role_code != "admin":
            raise HTTPException(status_code=403, detail="Solo un administrador puede asignar el rol admin")
        user.role_id = role.id
        user.role = role
        changes["role"] = role.code
    if payload.is_active is not None:
        if user.id == actor.id and payload.is_active is False:
            raise HTTPException(status_code=422, detail="No puede desactivar su propia cuenta")
        user.is_active = payload.is_active
        changes["is_active"] = payload.is_active

    await audit.record(
        action="users.update", module="users", user=actor, entity="user", entity_id=user.id,
        ip_address=client_context(request)["ip"], user_agent=request.headers.get("user-agent"),
        detail={"changes": changes}, session=session,
    )
    await session.commit()
    return user


@router.get("/stats/summary", summary="Resumen de usuarios por rol")
async def users_summary(
    _: CurrentUser = Depends(require("users:read")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, int | str]]:
    rows = await session.execute(
        select(Role.code, Role.name, func.count(User.id))
        .join(User, User.role_id == Role.id, isouter=True)
        .group_by(Role.code, Role.name)
        .order_by(Role.id)
    )
    return [{"role": code, "name": name, "users": total} for code, name, total in rows.all()]

@router.get("/{user_id}", response_model=UserOut, summary="Detalle de usuario")
async def get_user(
    user_id: uuid.UUID,
    _: CurrentUser = Depends(require("users:read")),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario inexistente")
    return user


@roles_router.get("", response_model=list[RoleOut], summary="Listar roles")
async def list_roles(
    _: CurrentUser = Depends(require("roles:read")),
    session: AsyncSession = Depends(get_session),
) -> list[Role]:
    return list((await session.execute(select(Role).order_by(Role.id))).scalars().all())


@roles_router.get("/{role_code}/permissions", response_model=list[PermissionOut], summary="Permisos del rol")
async def role_permissions(
    role_code: str,
    _: CurrentUser = Depends(require("roles:read")),
    session: AsyncSession = Depends(get_session),
) -> list[Permission]:
    role = (await session.execute(select(Role).where(Role.code == role_code))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Rol inexistente")
    rows = await session.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
        .order_by(Permission.module, Permission.action)
    )
    return list(rows.scalars().all())


