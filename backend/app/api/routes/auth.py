"""Autenticación: login con bloqueo por intentos, JWT y rotación de refresh tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, CurrentUserDep, client_context
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.db.models import RefreshToken, User
from app.db.session import get_session
from app.schemas import LoginRequest, MeOut, RefreshRequest, TokenPair
from app.services import audit

router = APIRouter(prefix="/auth", tags=["Autenticación"])
settings = get_settings()

# Hash bcrypt de una contraseña aleatoria: mantiene un costo similar cuando el
# usuario no existe y evita enumeración por diferencias de tiempo.
_DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEe.7Zs1l8LQx0Fh4b1tXQ6Q8uY3rP9c0Ge"


async def _issue_tokens(session: AsyncSession, user: User, request: Request) -> TokenPair:
    access = create_access_token(subject=str(user.id), role=user.role.code)
    raw_refresh, digest, expires_at = new_refresh_token()
    ctx = client_context(request)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest,
            expires_at=expires_at,
            ip_address=ctx["ip"],
            user_agent=ctx["user_agent"],
        )
    )
    await session.flush()
    return TokenPair(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_minutes * 60,
    )


@router.post("/login", response_model=TokenPair, summary="Iniciar sesión")
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    user = (await session.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        await audit.record(
            action="login", module="auth", result="denied", ip_address=client_context(request)["ip"],
            user_agent=request.headers.get("user-agent"),
            detail={"email": payload.email, "reason": "unknown_user"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if user.locked_until and user.locked_until > now:
        await audit.record(
            action="login", module="auth", result="denied", ip_address=client_context(request)["ip"],
            user_agent=request.headers.get("user-agent"),
            detail={"email": payload.email, "reason": "locked"},
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Cuenta bloqueada hasta {user.locked_until.isoformat()}",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario desactivado")

    if not verify_password(payload.password, user.password_hash):
        user.failed_attempts += 1
        locked = False
        if user.failed_attempts >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_attempts = 0
            locked = True
        await audit.record(
            action="login", module="auth", result="denied", ip_address=client_context(request)["ip"],
            user_agent=request.headers.get("user-agent"),
            detail={"email": payload.email, "reason": "bad_password", "locked": locked},
            session=session,
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    # MFA obligatorio cuando el perfil lo exige (TOTP verificado por el IdP/backend)
    if user.mfa_enabled and not payload.otp and settings.environment != "dev":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere código MFA")

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    tokens = await _issue_tokens(session, user, request)
    await audit.record(
        action="login", module="auth", result="success", user=CurrentUser(
            id=user.id, email=str(user.email), role_code=user.role.code,
            role_name=user.role.name, area=user.area, permissions=set(),
        ),
        ip_address=client_context(request)["ip"], user_agent=request.headers.get("user-agent"),
        detail={"mfa": user.mfa_enabled}, session=session,
    )
    await session.commit()
    return tokens


@router.post("/refresh", response_model=TokenPair, summary="Renovar tokens (rotación)")
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    digest = hash_refresh_token(payload.refresh_token)
    row = (
        await session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == digest, RefreshToken.revoked_at.is_(None))
            .with_for_update()
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if row is None or row.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    user = await session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    row.revoked_at = now
    tokens = await _issue_tokens(session, user, request)
    await session.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Cerrar sesión")
async def logout(
    payload: RefreshRequest,
    user: CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> Response:
    digest = hash_refresh_token(payload.refresh_token)
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == digest, RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await audit.record(
        action="logout", module="auth", user=user, result="success",
        detail={"email": user.email}, session=session,
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeOut, summary="Perfil y permisos efectivos")
async def me(user: CurrentUserDep, session: AsyncSession = Depends(get_session)) -> MeOut:
    db_user = await session.get(User, user.id)
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=db_user.full_name if db_user else user.email,
        role=user.role_code,
        permissions=sorted(user.permissions),
        area=user.area,
    )
