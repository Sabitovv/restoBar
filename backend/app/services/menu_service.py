import json
from pathlib import Path

from ..models import CafeInfo, MenuCategory, MenuItem, MenuItemVariant, Restaurant


def _read_json(path: str) -> list | dict:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as infile:
        return json.load(infile)


def get_cafe_info_from_pg() -> dict | None:
    restaurant = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.created_at.asc()).first()
    if restaurant is not None:
        hours = restaurant.working_hours_json or {}
        compact = " | ".join([f"{day}: {value}" for day, value in hours.items() if value])
        return {
            "name": restaurant.name,
            "kitchenCategories": restaurant.about or "",
            "rating": "4.9",
            "cookingTime": compact or "",
            "status": "Open" if restaurant.is_active else "Closed",
            "logoImage": restaurant.preview_image or "",
            "coverImage": restaurant.preview_image or "",
            "workingHours": hours,
            "previewImage": restaurant.preview_image or "",
        }

    row = CafeInfo.query.filter_by(id="main").first()
    if row is None:
        return None
    return row.payload_json


def get_categories_from_pg(metadata_path: str = "data/categories.json") -> list[dict]:
    metadata = _read_json(metadata_path)
    metadata_by_id = {item.get("id"): item for item in metadata if isinstance(item, dict)}

    categories = (
        MenuCategory.query.filter_by(is_active=True)
        .order_by(MenuCategory.id.asc())
        .all()
    )
    result = []
    for category in categories:
        meta = metadata_by_id.get(category.id, {})
        result.append(
            {
                "id": category.id,
                "name": category.name,
                "icon": meta.get("icon", ""),
                "backgroundColor": meta.get("backgroundColor", "#CCCCCC"),
            }
        )
    return result


def _variant_weight_from_json(menu_item_id: str, variant_name: str, menu_folder_path: str) -> str | None:
    folder_path = Path(menu_folder_path)
    if not folder_path.exists():
        return None
    for file_path in folder_path.glob("*.json"):
        payload = _read_json(str(file_path))
        if not isinstance(payload, list):
            continue
        for item in payload:
            if item.get("id") != menu_item_id:
                continue
            for variant in item.get("variants", []):
                if variant.get("name") == variant_name:
                    return variant.get("weight")
    return None


def get_category_menu_from_pg(category_id: str, menu_folder_path: str = "data/menu") -> list[dict]:
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
            weight = _variant_weight_from_json(item.id, variant.name, menu_folder_path)
            item_variants.append(
                {
                    "id": variant.id.split(":")[-1],
                    "name": variant.name,
                    "cost": str(variant.price_minor),
                    "weight": weight,
                }
            )
        result.append(
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "image": item.image,
                "variants": item_variants,
            }
        )

    return result


def get_menu_item_details_from_pg(menu_item_id: str, menu_folder_path: str = "data/menu") -> dict | None:
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
        "description": item.description,
        "image": item.image,
        "variants": [
            {
                "id": variant.id.split(":")[-1],
                "name": variant.name,
                "cost": str(variant.price_minor),
                "weight": _variant_weight_from_json(item.id, variant.name, menu_folder_path),
            }
            for variant in variants
        ],
    }
