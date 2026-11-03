"""Pruebas del control de acceso basado en roles (RBAC)."""
import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser, require


def make_user(permissions: set[str], role: str = "analyst") -> CurrentUser:
    return CurrentUser(
        id=uuid.UUID("00000000-0000-4000-8000-000000000003"),
        email="analista1@soclite.local",
        role_code=role,
        role_name="Analista SOC",
        area="SOC",
        permissions=permissions,
    )


def test_require_allows_when_permission_present():
    checker = require("alerts:read")
    user = make_user({"alerts:read", "triage:run"})
    assert asyncio.run(checker(user)) == user


def test_require_denies_when_permission_missing():
    checker = require("users:update")
    user = make_user({"alerts:read"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(checker(user))
    assert exc.value.status_code == 403
    assert exc.value.detail["missing"] == ["users:update"]


def test_require_all_mode_denies_if_one_is_missing():
    checker = require("alerts:read", "alerts:update", mode="all")
    user = make_user({"alerts:read"})
    with pytest.raises(HTTPException):
        asyncio.run(checker(user))


def test_require_any_mode_allows_one_permission():
    checker = require("reports:generate", "reports:download", mode="any")
    user = make_user({"reports:download"})
    assert asyncio.run(checker(user)) == user


def test_viewer_cannot_operate_alerts():
    viewer = make_user({"dashboard:read", "alerts:read"}, role="viewer")
    checker = require("alerts:update")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(checker(viewer))
    assert exc.value.status_code == 403
