from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import func

from ..extensions import db
from ..models import MenuCategory, MenuItem, MenuItemVariant, StaffRole
from .admin_auth_service import AdminPrincipal
from .admin_staff_service import StaffPermissionError


def _assert_menu_permissions(actor: AdminPrincipal) -> None:
    if actor.role not in {StaffRole.admin.value, StaffRole.manager.value}:
        raise StaffPermissionError("Insufficient permissions for menu management.", 403)


def _normalize_recipe(payload_recipe: object) -> list[str]:
    if payload_recipe is None:
        return []
    if isinstance(payload_recipe, str):
        chunks = payload_recipe.replace("\r", "\n").replace(",", "\n").split("\n")
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    if isinstance(payload_recipe, list):
        return [str(chunk).strip() for chunk in payload_recipe if str(chunk).strip()]
    raise StaffPermissionError("recipe must be a string list.", 400)


def _normalize_image(payload_image: object) -> str | None:
    if payload_image is None:
        return None
    image = str(payload_image).strip()
    if not image:
        return None
    if len(image) > 4_500_000:
        raise StaffPermissionError("image is too large. Max size is about 3 MB.", 400)
    return image


def _normalize_weight(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_restaurant_scope(actor: AdminPrincipal, restaurant_id: str | None) -> UUID:
    _assert_menu_permissions(actor)
    if restaurant_id and restaurant_id != actor.restaurant_id:
        raise StaffPermissionError("Forbidden restaurant scope.", 403)
    return UUID(actor.restaurant_id)


def list_menu_categories(actor: AdminPrincipal, restaurant_id: str | None) -> list[dict]:
    scope_id = resolve_restaurant_scope(actor, restaurant_id)
    counts = dict(
        db.session.query(MenuItem.category_id, func.count(MenuItem.id))
        .filter_by(restaurant_id=scope_id, is_active=True)
        .group_by(MenuItem.category_id)
        .all()
    )
    categories = (
        MenuCategory.query.filter_by(restaurant_id=scope_id)
        .order_by(MenuCategory.created_at.asc())
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "icon": c.icon,
            "backgroundColor": c.background_color,
            "isActive": c.is_active,
            "itemsCount": int(counts.get(c.id, 0)),
        }
        for c in categories
    ]


def create_menu_category(actor: AdminPrincipal, payload: dict) -> MenuCategory:
    scope_id = resolve_restaurant_scope(actor, payload.get("restaurantId"))
    name = (payload.get("name") or "").strip()
    if not name:
        raise StaffPermissionError("name is required.", 400)
    category = MenuCategory(
        id=(payload.get("id") or f"cat-{uuid.uuid4().hex[:8]}"),
        restaurant_id=scope_id,
        name=name,
        icon=(payload.get("icon") or None),
        background_color=(payload.get("backgroundColor") or None),
        is_active=bool(payload.get("isActive", True)),
    )
    db.session.add(category)
    return category


def update_menu_category(actor: AdminPrincipal, category_id: str, payload: dict) -> MenuCategory:
    scope_id = resolve_restaurant_scope(actor, payload.get("restaurantId"))
    category = MenuCategory.query.filter_by(id=category_id, restaurant_id=scope_id).first()
    if category is None:
        raise StaffPermissionError("Category not found in this restaurant.", 404)

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            raise StaffPermissionError("name cannot be empty.", 400)
        category.name = name
    if "isActive" in payload:
        category.is_active = bool(payload.get("isActive"))
    if "icon" in payload:
        category.icon = (payload.get("icon") or None)
    if "backgroundColor" in payload:
        category.background_color = (payload.get("backgroundColor") or None)
    return category


def list_menu_items(actor: AdminPrincipal, restaurant_id: str | None, category_id: str | None) -> list[dict]:
    scope_id = resolve_restaurant_scope(actor, restaurant_id)
    query = MenuItem.query.filter_by(restaurant_id=scope_id, is_active=True)
    if category_id:
        query = query.filter_by(category_id=category_id)
    items = query.order_by(MenuItem.created_at.asc()).all()
    if not items:
        return []

    item_ids = [item.id for item in items]
    variants = MenuItemVariant.query.filter(MenuItemVariant.menu_item_id.in_(item_ids)).order_by(MenuItemVariant.id.asc()).all()
    by_item: dict[str, list[MenuItemVariant]] = {}
    for variant in variants:
        by_item.setdefault(variant.menu_item_id, []).append(variant)

    return [
        {
            "id": item.id,
            "categoryId": item.category_id,
            "name": item.name,
            "description": item.description,
            "recipe": item.recipe,
            "image": item.image,
            "discountMinor": item.discount_minor,
            "discountIsActive": item.discount_is_active,
            "isActive": item.is_active,
            "isAvailableNow": item.is_available_now,
            "isPopular": item.is_popular,
            "variants": [
                {
                    "id": variant.id,
                    "name": variant.name,
                    "priceMinor": variant.price_minor,
                    "weight": variant.weight,
                    "currency": variant.currency,
                    "isActive": variant.is_active,
                }
                for variant in by_item.get(item.id, [])
            ],
        }
        for item in items
    ]


def create_menu_item(actor: AdminPrincipal, payload: dict) -> MenuItem:
    scope_id = resolve_restaurant_scope(actor, payload.get("restaurantId"))
    name = (payload.get("name") or "").strip()
    category_id = payload.get("categoryId")
    if not name or not category_id:
        raise StaffPermissionError("name and categoryId are required.", 400)

    category = MenuCategory.query.filter_by(id=category_id, restaurant_id=scope_id).first()
    if category is None:
        raise StaffPermissionError("Category not found in this restaurant.", 404)

    discount_minor = int(payload.get("discountMinor") or 0)
    if discount_minor < 0:
        raise StaffPermissionError("discountMinor must be >= 0.", 400)

    item_id = payload.get("id") or f"item-{uuid.uuid4().hex[:10]}"
    item = MenuItem(
        id=item_id,
        restaurant_id=scope_id,
        category_id=category_id,
        name=name,
        description=payload.get("description"),
        recipe=_normalize_recipe(payload.get("recipe")),
        image=_normalize_image(payload.get("image")),
        discount_minor=discount_minor,
        discount_is_active=bool(payload.get("discountIsActive", False)),
        is_active=bool(payload.get("isActive", True)),
        is_available_now=bool(payload.get("isAvailableNow", True)),
        is_popular=bool(payload.get("isPopular", False)),
    )
    db.session.add(item)

    for index, variant_payload in enumerate(payload.get("variants") or []):
        variant_name = (variant_payload.get("name") or "").strip()
        price_minor = variant_payload.get("priceMinor")
        if not variant_name or price_minor is None:
            raise StaffPermissionError("Each variant requires name and priceMinor.", 400)
        variant = MenuItemVariant(
            id=variant_payload.get("id") or f"{item_id}:v{index + 1}",
            menu_item_id=item.id,
            name=variant_name,
            price_minor=int(price_minor),
            weight=_normalize_weight(variant_payload.get("weight")),
            currency=(variant_payload.get("currency") or "USD").upper(),
            is_active=bool(variant_payload.get("isActive", True)),
        )
        db.session.add(variant)

    return item


def update_menu_item(actor: AdminPrincipal, menu_item_id: str, payload: dict) -> MenuItem:
    _assert_menu_permissions(actor)
    item = MenuItem.query.filter_by(id=menu_item_id, is_active=True).first()
    if item is None:
        raise StaffPermissionError("Menu item not found.", 404)
    if str(item.restaurant_id) != actor.restaurant_id:
        raise StaffPermissionError("Forbidden restaurant scope.", 403)

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            raise StaffPermissionError("name cannot be empty.", 400)
        item.name = name
    if "description" in payload:
        item.description = payload.get("description")
    if "recipe" in payload:
        item.recipe = _normalize_recipe(payload.get("recipe"))
    if "image" in payload:
        item.image = _normalize_image(payload.get("image"))
    if "isAvailableNow" in payload:
        item.is_available_now = bool(payload.get("isAvailableNow"))
    if "isPopular" in payload:
        item.is_popular = bool(payload.get("isPopular"))
    if "categoryId" in payload:
        category = MenuCategory.query.filter_by(id=payload.get("categoryId"), restaurant_id=item.restaurant_id).first()
        if category is None:
            raise StaffPermissionError("Category not found in this restaurant.", 404)
        item.category_id = payload.get("categoryId")
    if "discountMinor" in payload:
        discount_minor = int(payload.get("discountMinor") or 0)
        if discount_minor < 0:
            raise StaffPermissionError("discountMinor must be >= 0.", 400)
        item.discount_minor = discount_minor
    if "discountIsActive" in payload:
        item.discount_is_active = bool(payload.get("discountIsActive"))
    if "variants" in payload:
        variants_payload = payload.get("variants") or []
        if not variants_payload:
            raise StaffPermissionError("variants cannot be empty.", 400)
        variant_payload = variants_payload[0]
        variant_name = (variant_payload.get("name") or "default").strip()
        if not variant_name:
            raise StaffPermissionError("variant name cannot be empty.", 400)
        if variant_payload.get("priceMinor") is None:
            raise StaffPermissionError("variant priceMinor is required.", 400)
        variant = (
            MenuItemVariant.query.filter_by(menu_item_id=item.id, is_active=True)
            .order_by(MenuItemVariant.id.asc())
            .first()
        )
        if variant is None:
            variant = MenuItemVariant(
                id=f"{item.id}:v1",
                menu_item_id=item.id,
                name=variant_name,
                price_minor=int(variant_payload.get("priceMinor")),
                weight=_normalize_weight(variant_payload.get("weight")),
                currency=(variant_payload.get("currency") or "USD").upper(),
                is_active=True,
            )
            db.session.add(variant)
        else:
            variant.name = variant_name
            variant.price_minor = int(variant_payload.get("priceMinor"))
            variant.weight = _normalize_weight(variant_payload.get("weight"))
            variant.currency = (variant_payload.get("currency") or variant.currency or "USD").upper()

    return item


def soft_delete_menu_item(actor: AdminPrincipal, menu_item_id: str) -> MenuItem:
    _assert_menu_permissions(actor)
    item = MenuItem.query.filter_by(id=menu_item_id, is_active=True).first()
    if item is None:
        raise StaffPermissionError("Menu item not found.", 404)
    if str(item.restaurant_id) != actor.restaurant_id:
        raise StaffPermissionError("Forbidden restaurant scope.", 403)
    item.is_active = False
    item.is_available_now = False
    return item


def toggle_item_availability(actor: AdminPrincipal, menu_item_id: str, is_available_now: bool) -> MenuItem:
    _assert_menu_permissions(actor)
    item = MenuItem.query.filter_by(id=menu_item_id).first()
    if item is None:
        raise StaffPermissionError("Menu item not found.", 404)
    if actor.role != StaffRole.super_admin.value and str(item.restaurant_id) != actor.restaurant_id:
        raise StaffPermissionError("Forbidden restaurant scope.", 403)
    item.is_available_now = bool(is_available_now)
    return item
