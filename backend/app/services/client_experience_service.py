from __future__ import annotations

from datetime import datetime
from uuid import UUID

from ..extensions import db
from ..models import CafeInfo, ClientTheme, StaffRole
from .admin_auth_service import AdminPrincipal
from .admin_staff_service import StaffPermissionError


def _default_theme_config() -> dict:
    return {
        "themeKey": "classic",
        "palette": {
            "bg": "#fdf6ee",
            "surface": "#fffaf4",
            "text": "#2f241b",
            "muted": "#6f5f51",
            "primary": "#b25a2b",
            "accent": "#e29a4a",
        },
        "radius": {"card": 18, "pill": 999},
        "hero": {"title": "", "subtitle": ""},
        "popular": {"strategy": "db_flag", "limit": 10},
    }


def _ensure_admin(actor: AdminPrincipal) -> UUID:
    if actor.role not in {StaffRole.admin.value, StaffRole.manager.value, StaffRole.super_admin.value}:
        raise StaffPermissionError("Insufficient permissions.", 403)
    return UUID(actor.restaurant_id)


def get_client_theme_for_restaurant(restaurant_id: UUID) -> dict:
    theme = ClientTheme.query.filter_by(restaurant_id=restaurant_id).first()
    if theme is None:
        return _default_theme_config()
    return theme.config_json


def get_client_theme_public(restaurant_id: str | None) -> dict:
    if restaurant_id is not None:
        theme = ClientTheme.query.filter_by(restaurant_id=UUID(restaurant_id)).first()
        if theme is not None:
            return theme.config_json

    first = ClientTheme.query.order_by(ClientTheme.updated_at.desc()).first()
    if first is not None:
        return first.config_json
    return _default_theme_config()


def set_client_theme(actor: AdminPrincipal, payload: dict) -> dict:
    restaurant_id = _ensure_admin(actor)
    incoming = payload if isinstance(payload, dict) else {}
    current = get_client_theme_for_restaurant(restaurant_id)
    merged = {**current, **incoming}
    theme = ClientTheme.query.filter_by(restaurant_id=restaurant_id).first()
    if theme is None:
        theme = ClientTheme(restaurant_id=restaurant_id, config_json=merged)
        db.session.add(theme)
    else:
        theme.config_json = merged
        theme.updated_at = datetime.utcnow()
    return merged


def get_cafe_info_payload() -> dict | None:
    row = CafeInfo.query.filter_by(id="main").first()
    if row is None:
        return None
    return row.payload_json


def set_cafe_info_payload(actor: AdminPrincipal, payload: dict) -> dict:
    _ensure_admin(actor)
    if not isinstance(payload, dict):
        raise StaffPermissionError("Payload must be object.", 400)
    row = CafeInfo.query.filter_by(id="main").first()
    if row is None:
        row = CafeInfo(id="main", payload_json=payload)
        db.session.add(row)
    else:
        row.payload_json = payload
    return row.payload_json
