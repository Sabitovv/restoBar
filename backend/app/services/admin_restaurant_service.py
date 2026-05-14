from __future__ import annotations

import re
from uuid import UUID

from ..extensions import db
from ..models import Restaurant, StaffRole
from .admin_auth_service import AdminPrincipal
from .admin_staff_service import StaffPermissionError


def _ensure_super_admin(actor: AdminPrincipal) -> None:
    if actor.role != StaffRole.super_admin.value:
        raise StaffPermissionError("Only super admin can manage restaurants.", 403)


def list_restaurants(actor: AdminPrincipal) -> list[dict]:
    if actor.role == StaffRole.super_admin.value:
        items = Restaurant.query.order_by(Restaurant.created_at.asc()).all()
    else:
        items = Restaurant.query.filter_by(id=UUID(actor.restaurant_id)).all()

    return [
        {
            "id": str(item.id),
            "name": item.name,
            "slug": item.slug,
            "about": item.about,
            "aboutI18n": item.about_i18n or {"kk": "", "ru": item.about or "", "en": ""},
            "previewImage": item.preview_image,
            "workingHours": item.working_hours_json,
            "isActive": item.is_active,
        }
        for item in items
    ]


def _normalize_image(payload_image: object) -> str | None:
    if payload_image is None:
        return None
    image = str(payload_image).strip()
    if not image:
        return None
    if len(image) > 4_500_000:
        raise StaffPermissionError("image is too large. Max size is about 3 MB.", 400)
    return image


def _normalize_i18n_text(payload: object, field_name: str) -> dict[str, str]:
    if payload is None:
        return {"kk": "", "ru": "", "en": ""}
    if not isinstance(payload, dict):
        raise StaffPermissionError(f"{field_name} must be an object.", 400)
    return {
        "kk": str(payload.get("kk") or "").strip(),
        "ru": str(payload.get("ru") or "").strip(),
        "en": str(payload.get("en") or "").strip(),
    }


def _normalize_working_hours(payload: object) -> dict[str, dict[str, object]]:
    if not isinstance(payload, dict):
        raise StaffPermissionError("workingHours must be an object.", 400)

    result: dict[str, dict[str, object]] = {}
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        day_payload = payload.get(day) or {}
        if not isinstance(day_payload, dict):
            raise StaffPermissionError(f"workingHours.{day} must be an object.", 400)

        is_open = bool(day_payload.get("isOpen", True))
        open_at = str(day_payload.get("openAt") or "").strip()
        close_at = str(day_payload.get("closeAt") or "").strip()
        if is_open:
            if not re.match(r"^\d{2}:\d{2}$", open_at) or not re.match(r"^\d{2}:\d{2}$", close_at):
                raise StaffPermissionError(f"workingHours.{day} time format must be HH:MM.", 400)
            if open_at >= close_at:
                raise StaffPermissionError(f"workingHours.{day} openAt must be earlier than closeAt.", 400)
        else:
            open_at = ""
            close_at = ""

        result[day] = {
            "isOpen": is_open,
            "openAt": open_at,
            "closeAt": close_at,
        }
    return result


def get_restaurant_profile(actor: AdminPrincipal) -> dict:
    if actor.role == StaffRole.super_admin.value:
        raise StaffPermissionError("Only admin or manager can edit restaurant profile.", 403)
    restaurant = Restaurant.query.filter_by(id=UUID(actor.restaurant_id)).first()
    if restaurant is None:
        raise StaffPermissionError("Restaurant not found.", 404)
    return {
        "id": str(restaurant.id),
        "name": restaurant.name,
        "slug": restaurant.slug,
        "about": restaurant.about or "",
        "aboutI18n": restaurant.about_i18n or {"kk": "", "ru": restaurant.about or "", "en": ""},
        "previewImage": restaurant.preview_image,
        "workingHours": restaurant.working_hours_json or {},
        "isActive": restaurant.is_active,
    }


def update_restaurant_profile(actor: AdminPrincipal, payload: dict) -> dict:
    if actor.role == StaffRole.super_admin.value:
        raise StaffPermissionError("Only admin or manager can edit restaurant profile.", 403)
    restaurant = Restaurant.query.filter_by(id=UUID(actor.restaurant_id)).first()
    if restaurant is None:
        raise StaffPermissionError("Restaurant not found.", 404)

    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise StaffPermissionError("name is required.", 400)
        restaurant.name = name
    if "about" in payload:
        restaurant.about = str(payload.get("about") or "").strip()
    if "aboutI18n" in payload:
        restaurant.about_i18n = _normalize_i18n_text(payload.get("aboutI18n"), "aboutI18n")
    if "previewImage" in payload:
        restaurant.preview_image = _normalize_image(payload.get("previewImage"))
    if "workingHours" in payload:
        restaurant.working_hours_json = _normalize_working_hours(payload.get("workingHours") or {})

    return get_restaurant_profile(actor)


def create_restaurant(actor: AdminPrincipal, payload: dict) -> Restaurant:
    _ensure_super_admin(actor)
    name = (payload.get("name") or "").strip()
    slug = (payload.get("slug") or "").strip().lower()
    if not name or not slug:
        raise StaffPermissionError("name and slug are required.", 400)

    exists = Restaurant.query.filter_by(slug=slug).first()
    if exists is not None:
        raise StaffPermissionError("Restaurant slug already exists.", 409)

    restaurant = Restaurant(name=name, slug=slug, is_active=bool(payload.get("isActive", True)))
    db.session.add(restaurant)
    return restaurant


def delete_restaurant(actor: AdminPrincipal, restaurant_id: str) -> Restaurant:
    _ensure_super_admin(actor)
    restaurant = Restaurant.query.filter_by(id=UUID(restaurant_id)).first()
    if restaurant is None:
        raise StaffPermissionError("Restaurant not found.", 404)
    restaurant.is_active = False
    return restaurant
