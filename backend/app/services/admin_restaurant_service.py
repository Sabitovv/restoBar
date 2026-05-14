from __future__ import annotations

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
            "isActive": item.is_active,
        }
        for item in items
    ]


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
