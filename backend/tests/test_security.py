"""Pruebas unitarias de seguridad: política de contraseñas y JWT."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    password_policy_errors,
    verify_password,
)


def test_password_policy_accepts_strong_password():
    assert password_policy_errors("SocLite#2026!") == []


@pytest.mark.parametrize(
    "password, expected_fragment",
    [
        ("corta", "12 caracteres"),
        ("solominusculas1!", "mayúscula"),
        ("SINMINUSCULAS1!", "minúscula"),
        ("SinDigitos!!", "dígito"),
        ("SinSimbolos123", "símbolo"),
    ],
)
def test_password_policy_rejects_weak_passwords(password, expected_fragment):
    errors = password_policy_errors(password)
    assert any(expected_fragment in error for error in errors)


def test_password_hash_roundtrip():
    hashed = hash_password("SocLite#2026!")
    assert hashed != "SocLite#2026!"
    assert verify_password("SocLite#2026!", hashed)
    assert not verify_password("otra-clave", hashed)


def test_invalid_hash_is_rejected_without_exception():
    assert not verify_password("SocLite#2026!", "no-es-un-hash")


def test_access_token_contains_role_and_type():
    token = create_access_token(subject="00000000-0000-4000-8000-000000000003", role="analyst")
    payload = decode_token(token)
    assert payload["role"] == "analyst"
    assert payload["type"] == "access"
    assert payload["sub"].endswith("0003")


def test_expired_token_is_rejected():
    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "00000000-0000-4000-8000-000000000003",
            "role": "analyst",
            "type": "access",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_refresh_token_cannot_be_used_as_access():
    token = create_access_token(subject="00000000-0000-4000-8000-000000000003", role="analyst")
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, expected_type="refresh")
