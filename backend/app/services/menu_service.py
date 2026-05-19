import json
import re
from pathlib import Path

from ..models import CafeInfo, MenuCategory, MenuItem, MenuItemVariant, Restaurant


def _pick_i18n_text(i18n_value: dict | None, fallback: str | None, lang: str) -> str:
    data = i18n_value if isinstance(i18n_value, dict) else {}
    wanted = str(data.get(lang) or "").strip()
    if wanted:
        return wanted
    for code in ["ru", "kk", "en"]:
        value = str(data.get(code) or "").strip()
        if value:
            return value
    return str(fallback or "").strip()


def _pick_i18n_recipe(i18n_value: dict | None, fallback: list[str] | None, lang: str) -> list[str]:
    data = i18n_value if isinstance(i18n_value, dict) else {}
    raw = data.get(lang)
    if isinstance(raw, list):
        prepared = [str(part).strip() for part in raw if str(part).strip()]
        if prepared:
            return prepared
    for code in ["ru", "kk", "en"]:
        raw_alt = data.get(code)
        if isinstance(raw_alt, list):
            prepared = [str(part).strip() for part in raw_alt if str(part).strip()]
            if prepared:
                return prepared
    return fallback or []


def _resolve_price(item: MenuItem, fallback_price_minor: int, currency: str) -> tuple[int, str]:
    price_map = item.price_by_currency if isinstance(item.price_by_currency, dict) else {}
    currency_norm = (currency or "KZT").upper()
    if currency_norm in price_map:
        return int(price_map[currency_norm]), currency_norm
    if "KZT" in price_map:
        return int(price_map["KZT"]), "KZT"
    return fallback_price_minor, "KZT"


def _read_json(path: str) -> list | dict:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as infile:
        return json.load(infile)


def _to_hhmm(value: str) -> str:
    raw = str(value or "").strip()
    match = re.match(r"^(\d{1,2}):(\d{2})$", raw)
    if not match:
        return ""
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return ""
    return f"{hour:02d}:{minute:02d}"


def _normalize_working_hours_for_client(raw_hours: object) -> dict[str, dict[str, object]]:
    day_keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    result: dict[str, dict[str, object]] = {
        day: {"isOpen": False, "openAt": "", "closeAt": ""}
        for day in day_keys
    }

    if not isinstance(raw_hours, dict):
        return result

    for day in day_keys:
        payload = raw_hours.get(day)
        if isinstance(payload, dict):
            is_open = bool(payload.get("isOpen"))
            open_at = _to_hhmm(str(payload.get("openAt") or ""))
            close_at = _to_hhmm(str(payload.get("closeAt") or ""))
            if is_open and open_at and close_at:
                result[day] = {"isOpen": True, "openAt": open_at, "closeAt": close_at}
            continue

        if isinstance(payload, str):
            # Legacy format example: "Mon 9:00-00:00"
            found = re.search(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", payload)
            if not found:
                continue
            open_at = _to_hhmm(found.group(1))
            close_at = _to_hhmm(found.group(2))
            if open_at and close_at:
                result[day] = {"isOpen": True, "openAt": open_at, "closeAt": close_at}

    return result


def get_cafe_info_from_pg(lang: str = "ru") -> dict | None:
    restaurant = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.created_at.asc()).first()
    if restaurant is not None:
        hours = _normalize_working_hours_for_client(restaurant.working_hours_json or {})
        compact = " | ".join([
            f"{day}: {value.get('openAt')}-{value.get('closeAt')}" if value.get("isOpen") else f"{day}: closed"
            for day, value in hours.items()
        ])
        return {
            "name": restaurant.name,
            "kitchenCategories": _pick_i18n_text(restaurant.about_i18n, restaurant.about, lang),
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


def get_categories_from_pg(lang: str = "ru", metadata_path: str = "data/categories.json") -> list[dict]:
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
                "name": _pick_i18n_text(category.name_i18n, category.name, lang),
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


def get_category_menu_from_pg(category_id: str, lang: str = "ru", currency: str = "KZT", menu_folder_path: str = "data/menu") -> list[dict] | None:
    category_exists = MenuCategory.query.filter_by(id=category_id, is_active=True).first() is not None
    if not category_exists:
        return None

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
            price_minor, used_currency = _resolve_price(item, int(variant.price_minor), currency)
            item_variants.append(
                {
                    "id": variant.id.split(":")[-1],
                    "name": variant.name,
                    "cost": str(price_minor),
                    "currency": used_currency,
                    "weight": weight,
                }
            )
        result.append(
            {
                "id": item.id,
                "name": _pick_i18n_text(item.name_i18n, item.name, lang),
                "description": _pick_i18n_text(item.description_i18n, item.description, lang),
                "recipe": _pick_i18n_recipe(item.recipe_i18n, item.recipe, lang),
                "image": item.image,
                "variants": item_variants,
            }
        )

    return result


def get_menu_item_details_from_pg(menu_item_id: str, lang: str = "ru", currency: str = "KZT", menu_folder_path: str = "data/menu") -> dict | None:
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
        "name": _pick_i18n_text(item.name_i18n, item.name, lang),
        "description": _pick_i18n_text(item.description_i18n, item.description, lang),
        "recipe": _pick_i18n_recipe(item.recipe_i18n, item.recipe, lang),
        "image": item.image,
        "variants": [
            {
                "id": variant.id.split(":")[-1],
                "name": variant.name,
                "cost": str(_resolve_price(item, int(variant.price_minor), currency)[0]),
                "currency": _resolve_price(item, int(variant.price_minor), currency)[1],
                "weight": _variant_weight_from_json(item.id, variant.name, menu_folder_path),
            }
            for variant in variants
        ],
    }


def get_popular_menu_from_pg(limit: int = 8, lang: str = "ru", currency: str = "KZT", menu_folder_path: str = "data/menu") -> list[dict]:
    items = (
        MenuItem.query.filter_by(is_active=True, is_available_now=True)
        .order_by(MenuItem.id.asc())
        .limit(max(1, int(limit or 8)))
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
        base_variant = (variants_by_item_id.get(item.id) or [None])[0]
        if base_variant is None:
            continue
        price_minor, used_currency = _resolve_price(item, int(base_variant.price_minor), currency)
        result.append(
            {
                "id": item.id,
                "name": _pick_i18n_text(item.name_i18n, item.name, lang),
                "description": _pick_i18n_text(item.description_i18n, item.description, lang),
                "recipe": _pick_i18n_recipe(item.recipe_i18n, item.recipe, lang),
                "image": item.image,
                "variants": [
                    {
                        "id": base_variant.id.split(":")[-1],
                        "name": base_variant.name,
                        "cost": str(price_minor),
                        "currency": used_currency,
                        "weight": _variant_weight_from_json(item.id, base_variant.name, menu_folder_path),
                    }
                ],
            }
        )
    return result
