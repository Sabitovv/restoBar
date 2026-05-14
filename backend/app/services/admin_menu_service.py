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


def _normalize_recipe_i18n(payload: object) -> dict[str, list[str]]:
    if payload is None:
        return {"kk": [], "ru": [], "en": []}
    if not isinstance(payload, dict):
        raise StaffPermissionError("recipeI18n must be an object.", 400)
    result: dict[str, list[str]] = {}
    for lang in ["kk", "ru", "en"]:
        result[lang] = _normalize_recipe(payload.get(lang))
    return result


def _normalize_price_by_currency(payload: object, fallback_price_minor: int | None = None) -> dict[str, int]:
    if payload is None:
        if fallback_price_minor is None:
            raise StaffPermissionError("priceByCurrency is required.", 400)
        return {"KZT": int(fallback_price_minor)}
    if not isinstance(payload, dict):
        raise StaffPermissionError("priceByCurrency must be an object.", 400)
    normalized: dict[str, int] = {}
    for code, value in payload.items():
        code_norm = str(code or "").upper().strip()
        if len(code_norm) != 3:
            raise StaffPermissionError("Currency code must be 3 letters.", 400)
        amount = int(value)
        if amount < 0:
            raise StaffPermissionError("Currency amount must be >= 0.", 400)
        normalized[code_norm] = amount
    if "KZT" not in normalized:
        raise StaffPermissionError("priceByCurrency must include KZT.", 400)
    return normalized


def _normalize_image(payload_image: object) -> str | None:
    if payload_image is None:
        return None
    image = str(payload_image).strip()
    if not image:
        return None
    if len(image) > 4_500_000:
        raise StaffPermissionError("image is too large. Max size is about 3 MB.", 400)
    return image


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
        .order_by(MenuCategory.sort_order.asc(), MenuCategory.created_at.asc())
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "nameI18n": c.name_i18n or {"kk": "", "ru": c.name, "en": ""},
            "image": c.image,
            "sortOrder": c.sort_order,
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
    max_order = (
        db.session.query(func.max(MenuCategory.sort_order))
        .filter_by(restaurant_id=scope_id)
        .scalar()
    )
    name_i18n = _normalize_i18n_text(payload.get("nameI18n"), "nameI18n")
    if not name_i18n.get("ru"):
        name_i18n["ru"] = name

    category = MenuCategory(
        id=(payload.get("id") or f"cat-{uuid.uuid4().hex[:8]}"),
        restaurant_id=scope_id,
        name=name,
        name_i18n=name_i18n,
        image=_normalize_image(payload.get("image")),
        sort_order=int(max_order or 0) + 1,
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
    if "nameI18n" in payload:
        normalized_name_i18n = _normalize_i18n_text(payload.get("nameI18n"), "nameI18n")
        if not normalized_name_i18n.get("ru"):
            normalized_name_i18n["ru"] = category.name
        category.name_i18n = normalized_name_i18n
    if "isActive" in payload:
        category.is_active = bool(payload.get("isActive"))
    if "image" in payload:
        category.image = _normalize_image(payload.get("image"))
    return category


def reorder_menu_categories(actor: AdminPrincipal, payload: dict) -> list[dict]:
    scope_id = resolve_restaurant_scope(actor, payload.get("restaurantId"))
    ids = payload.get("ids")
    if not isinstance(ids, list) or not ids:
        raise StaffPermissionError("ids list is required.", 400)

    categories = MenuCategory.query.filter_by(restaurant_id=scope_id).all()
    by_id = {category.id: category for category in categories}
    if set(ids) != set(by_id.keys()):
        raise StaffPermissionError("ids must contain all category ids for this restaurant.", 400)

    for index, category_id in enumerate(ids, start=1):
        by_id[category_id].sort_order = index

    ordered = sorted(by_id.values(), key=lambda item: item.sort_order)
    return [
        {
            "id": c.id,
            "name": c.name,
            "nameI18n": c.name_i18n or {"kk": "", "ru": c.name, "en": ""},
            "image": c.image,
            "sortOrder": c.sort_order,
            "isActive": c.is_active,
        }
        for c in ordered
    ]


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
            "nameI18n": item.name_i18n or {"kk": "", "ru": item.name, "en": ""},
            "description": item.description,
            "descriptionI18n": item.description_i18n or {"kk": "", "ru": item.description or "", "en": ""},
            "recipe": item.recipe,
            "recipeI18n": item.recipe_i18n or {"kk": [], "ru": item.recipe or [], "en": []},
            "image": item.image,
            "priceByCurrency": item.price_by_currency or {},
            "discountMinor": item.discount_minor,
            "discountIsActive": item.discount_is_active,
            "isActive": item.is_active,
            "isAvailableNow": item.is_available_now,
            "variants": [
                {
                    "id": variant.id,
                    "name": variant.name,
                    "priceMinor": variant.price_minor,
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
    name_i18n = _normalize_i18n_text(payload.get("nameI18n"), "nameI18n")
    if not name_i18n.get("ru"):
        name_i18n["ru"] = name
    description_i18n = _normalize_i18n_text(payload.get("descriptionI18n"), "descriptionI18n")
    if not description_i18n.get("ru"):
        description_i18n["ru"] = str(payload.get("description") or "")
    recipe_i18n = _normalize_recipe_i18n(payload.get("recipeI18n"))
    if not recipe_i18n.get("ru"):
        recipe_i18n["ru"] = _normalize_recipe(payload.get("recipe"))

    item = MenuItem(
        id=item_id,
        restaurant_id=scope_id,
        category_id=category_id,
        name=name,
        name_i18n=name_i18n,
        description=payload.get("description"),
        description_i18n=description_i18n,
        recipe=_normalize_recipe(payload.get("recipe")),
        recipe_i18n=recipe_i18n,
        image=_normalize_image(payload.get("image")),
        price_by_currency=_normalize_price_by_currency(payload.get("priceByCurrency"), payload.get("variants", [{}])[0].get("priceMinor")),
        discount_minor=discount_minor,
        discount_is_active=bool(payload.get("discountIsActive", False)),
        is_active=bool(payload.get("isActive", True)),
        is_available_now=bool(payload.get("isAvailableNow", True)),
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
            currency=(variant_payload.get("currency") or "KZT").upper(),
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
    if "nameI18n" in payload:
        normalized_name_i18n = _normalize_i18n_text(payload.get("nameI18n"), "nameI18n")
        if not normalized_name_i18n.get("ru"):
            normalized_name_i18n["ru"] = item.name
        item.name_i18n = normalized_name_i18n
    if "description" in payload:
        item.description = payload.get("description")
    if "descriptionI18n" in payload:
        normalized_description_i18n = _normalize_i18n_text(payload.get("descriptionI18n"), "descriptionI18n")
        if not normalized_description_i18n.get("ru"):
            normalized_description_i18n["ru"] = item.description or ""
        item.description_i18n = normalized_description_i18n
    if "recipe" in payload:
        item.recipe = _normalize_recipe(payload.get("recipe"))
    if "recipeI18n" in payload:
        normalized_recipe_i18n = _normalize_recipe_i18n(payload.get("recipeI18n"))
        if not normalized_recipe_i18n.get("ru"):
            normalized_recipe_i18n["ru"] = item.recipe or []
        item.recipe_i18n = normalized_recipe_i18n
    if "image" in payload:
        item.image = _normalize_image(payload.get("image"))
    if "isAvailableNow" in payload:
        item.is_available_now = bool(payload.get("isAvailableNow"))
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
    if "priceByCurrency" in payload:
        item.price_by_currency = _normalize_price_by_currency(payload.get("priceByCurrency"))
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
                currency=(variant_payload.get("currency") or "KZT").upper(),
                is_active=True,
            )
            db.session.add(variant)
        else:
            variant.name = variant_name
            variant.price_minor = int(variant_payload.get("priceMinor"))
            variant.currency = (variant_payload.get("currency") or variant.currency or "KZT").upper()

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
