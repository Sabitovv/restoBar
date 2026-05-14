import json
from pathlib import Path

from ..models import CafeInfo, MenuCategory, MenuItem, MenuItemVariant


def _read_json(path: str) -> list | dict:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as infile:
        return json.load(infile)


def get_cafe_info_from_pg() -> dict | None:
    row = CafeInfo.query.filter_by(id="main").first()
    if row is None:
        return None
    return row.payload_json


def get_categories_from_pg() -> list[dict]:
    categories = (
        MenuCategory.query.filter_by(is_active=True)
        .order_by(MenuCategory.created_at.asc())
        .all()
    )
    return [
        {
            "id": category.id,
            "name": category.name,
            "icon": category.icon or "",
            "backgroundColor": category.background_color or "#CCCCCC",
            "isActive": category.is_active,
        }
        for category in categories
    ]


def get_category_menu_from_pg(category_id: str) -> list[dict]:
    items = (
        MenuItem.query.filter_by(category_id=category_id, is_active=True, is_available_now=True)
        .order_by(MenuItem.id.asc())
        .all()
    )
    if not items:
        return []

    item_ids = [item.id for item in items]
    variants = (
        MenuItemVariant.query.filter(MenuItemVariant.menu_item_id.in_(item_ids), MenuItemVariant.is_active.is_(True))
        .order_by(MenuItemVariant.id.asc())
        .all()
    )
    variants_by_item_id: dict[str, list[MenuItemVariant]] = {}
    for variant in variants:
        variants_by_item_id.setdefault(variant.menu_item_id, []).append(variant)

    result = []
    for item in items:
        item_variants = []
        for variant in variants_by_item_id.get(item.id, []):
            item_variants.append(
                {
                    "id": variant.id.split(":")[-1],
                    "name": variant.name,
                    "cost": str(variant.price_minor),
                    "weight": variant.weight,
                    "currency": variant.currency,
                }
            )
        result.append(
            {
                "id": item.id,
                "name": item.name,
                "categoryId": item.category_id,
                "description": item.description,
                "image": item.image,
                "isAvailableNow": item.is_available_now,
                "variants": item_variants,
            }
        )

    return result


def get_popular_menu_from_pg(limit: int = 10) -> list[dict]:
    safe_limit = max(1, min(int(limit), 50))
    items = (
        MenuItem.query.filter_by(is_active=True, is_available_now=True, is_popular=True)
        .order_by(MenuItem.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    if not items:
        items = (
        MenuItem.query.filter_by(is_active=True, is_available_now=True)
        .order_by(MenuItem.created_at.desc())
        .limit(safe_limit)
        .all()
        )
    if not items:
        return []

    item_ids = [item.id for item in items]
    variants = (
        MenuItemVariant.query.filter(MenuItemVariant.menu_item_id.in_(item_ids), MenuItemVariant.is_active.is_(True))
        .order_by(MenuItemVariant.id.asc())
        .all()
    )
    variants_by_item_id: dict[str, list[MenuItemVariant]] = {}
    for variant in variants:
        variants_by_item_id.setdefault(variant.menu_item_id, []).append(variant)

    result = []
    for item in items:
        item_variants = []
        for variant in variants_by_item_id.get(item.id, []):
            item_variants.append(
                {
                    "id": variant.id.split(":")[-1],
                    "name": variant.name,
                    "cost": str(variant.price_minor),
                    "weight": variant.weight,
                    "currency": variant.currency,
                }
            )
        result.append(
            {
                "id": item.id,
                "name": item.name,
                "categoryId": item.category_id,
                "description": item.description,
                "image": item.image,
                "isAvailableNow": item.is_available_now,
                "variants": item_variants,
            }
        )

    return result


def get_menu_item_details_from_pg(menu_item_id: str) -> dict | None:
    item = MenuItem.query.filter_by(id=menu_item_id, is_active=True, is_available_now=True).first()
    if item is None:
        return None
    variants = (
        MenuItemVariant.query.filter_by(menu_item_id=item.id, is_active=True)
        .order_by(MenuItemVariant.id.asc())
        .all()
    )
    return {
        "id": item.id,
        "name": item.name,
        "categoryId": item.category_id,
        "description": item.description,
        "image": item.image,
        "isAvailableNow": item.is_available_now,
        "variants": [
            {
                "id": variant.id.split(":")[-1],
                "name": variant.name,
                "cost": str(variant.price_minor),
                "weight": variant.weight,
                "currency": variant.currency,
            }
            for variant in variants
        ],
    }
