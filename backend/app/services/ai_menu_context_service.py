from __future__ import annotations

from ..models import MenuCategory, MenuItem, MenuItemVariant, Restaurant


def _format_hours(day: str, value: object) -> str | None:
    if isinstance(value, dict):
        is_open = bool(value.get("isOpen", False))
        if not is_open:
            return f"Hours {day}: closed"
        open_at = str(value.get("openAt") or "").strip()
        close_at = str(value.get("closeAt") or "").strip()
        if open_at and close_at:
            return f"Hours {day}: {open_at}-{close_at}"
        return f"Hours {day}: open"
    text = str(value or "").strip()
    if text:
        return f"Hours {day}: {text}"
    return None


def build_public_menu_facts(max_items: int = 80) -> list[str]:
    restaurant = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.created_at.asc()).first()
    if restaurant is None:
        return []

    facts: list[str] = []
    facts.append(f"Restaurant: {restaurant.name}")
    if restaurant.about:
        facts.append(f"About: {restaurant.about}")

    hours = restaurant.working_hours_json or {}
    if isinstance(hours, dict):
        for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
            hours_fact = _format_hours(day, hours.get(day))
            if hours_fact:
                facts.append(hours_fact)

    categories = (
        MenuCategory.query.filter_by(restaurant_id=restaurant.id, is_active=True)
        .order_by(MenuCategory.sort_order.asc(), MenuCategory.created_at.asc())
        .all()
    )
    category_name_by_id = {category.id: category.name for category in categories}
    for category in categories:
        facts.append(f"Category: {category.name}")

    items = (
        MenuItem.query.filter_by(restaurant_id=restaurant.id, is_active=True, is_available_now=True)
        .order_by(MenuItem.created_at.asc())
        .limit(max_items)
        .all()
    )
    item_ids = [item.id for item in items]
    variants = (
        MenuItemVariant.query.filter(MenuItemVariant.menu_item_id.in_(item_ids), MenuItemVariant.is_active.is_(True))
        .order_by(MenuItemVariant.id.asc())
        .all()
        if item_ids
        else []
    )
    first_variant_by_item_id: dict[str, MenuItemVariant] = {}
    for variant in variants:
        if variant.menu_item_id not in first_variant_by_item_id:
            first_variant_by_item_id[variant.menu_item_id] = variant

    for item in items:
        category_name = category_name_by_id.get(item.category_id, "Other")
        base_price = int(first_variant_by_item_id.get(item.id).price_minor) if item.id in first_variant_by_item_id else 0
        discount = int(item.discount_minor or 0) if item.discount_is_active else 0
        final_price = max(0, base_price - discount)
        facts.append(f"Dish: {item.name} | category: {category_name} | price: {final_price} {first_variant_by_item_id.get(item.id).currency if item.id in first_variant_by_item_id else 'USD'}")
        if item.description:
            facts.append(f"Dish description {item.name}: {item.description}")
        if isinstance(item.recipe, list) and item.recipe:
            facts.append(f"Dish ingredients {item.name}: {', '.join([str(part) for part in item.recipe[:12]])}")

    return facts[: max_items * 3]
