"""Primitivas de seguridad: hashing de contraseñas, JWT y tokens de refresco."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    """Genera un hash bcrypt. El costo 12 mantiene ~250 ms por verificación."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        # Hash inválido o algoritmo no soportado: se trata como credencial inválida
        return False


def password_policy_errors(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < 12:
        errors.append("La contraseña debe tener al menos 12 caracteres.")
    if not any(c.islower() for c in password):
        errors.append("Debe incluir al menos una minúscula.")
    if not any(c.isupper() for c in password):
        errors.append("Debe incluir al menos una mayúscula.")
    if not any(c.isdigit() for c in password):
        errors.append("Debe incluir al menos un dígito.")
    if not any(c in "!@#$%^&*()_+-=[]{};:,.<>?" for c in password):
        errors.append("Debe incluir al menos un símbolo.")
    return errors


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        "jti": secrets.token_hex(16),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub", "type"]},
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Tipo de token incorrecto")
    return payload


def new_refresh_token() -> tuple[str, str, datetime]:
    """Devuelve (token_en_claro, hash_sha256, expiración). Solo se persiste el hash."""
    settings = get_settings()
    raw = secrets.token_urlsafe(48)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, digest, datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
