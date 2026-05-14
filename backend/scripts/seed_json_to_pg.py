import json
from pathlib import Path

from app.main import app
from app.extensions import db
from app.models import CafeInfo, MenuCategory, MenuItem, MenuItemVariant, Restaurant


def run() -> None:
    base = Path(__file__).resolve().parents[1] / "data"
    with app.app_context():
        restaurant = Restaurant.query.filter_by(slug="main").first()
        if restaurant is None:
            raise RuntimeError("Restaurant with slug 'main' not found. Run migrations first.")

        info_payload = json.loads((base / "info.json").read_text(encoding="utf-8"))
        existing_info = CafeInfo.query.filter_by(id="main").first()
        if existing_info is None:
            db.session.add(CafeInfo(id="main", payload_json=info_payload))
        else:
            existing_info.payload_json = info_payload

        categories = json.loads((base / "categories.json").read_text(encoding="utf-8"))
        category_meta = {item["id"]: item for item in categories if isinstance(item, dict) and item.get("id")}
        for category in categories:
            existing_category = MenuCategory.query.filter_by(id=category["id"]).first()
            if existing_category is None:
                existing_category = MenuCategory(
                    id=category["id"],
                    restaurant_id=restaurant.id,
                    name=category["name"],
                    icon=category.get("icon"),
                    background_color=category.get("backgroundColor"),
                )
                db.session.add(existing_category)
            else:
                existing_category.restaurant_id = restaurant.id
                existing_category.name = category["name"]
                existing_category.icon = category.get("icon")
                existing_category.background_color = category.get("backgroundColor")

        popular_ids = set()
        popular_file = base / "menu" / "popular.json"
        if popular_file.exists():
            popular_payload = json.loads(popular_file.read_text(encoding="utf-8"))
            popular_ids = {item.get("id") for item in popular_payload if isinstance(item, dict) and item.get("id")}

        for menu_file in (base / "menu").glob("*.json"):
            if menu_file.stem == "popular":
                continue
            menu_items = json.loads(menu_file.read_text(encoding="utf-8"))
            category_id = menu_file.stem
            for item in menu_items:
                existing_item = MenuItem.query.filter_by(id=item["id"]).first()
                if existing_item is None:
                    existing_item = MenuItem(
                        id=item["id"],
                        restaurant_id=restaurant.id,
                        category_id=category_id,
                        name=item["name"],
                        description=item.get("description"),
                        image=item.get("image"),
                        is_popular=item["id"] in popular_ids,
                    )
                    db.session.add(existing_item)
                else:
                    existing_item.restaurant_id = restaurant.id
                    existing_item.category_id = category_id
                    existing_item.name = item["name"]
                    existing_item.description = item.get("description")
                    existing_item.image = item.get("image")
                    existing_item.is_popular = item["id"] in popular_ids

                for variant in item.get("variants", []):
                    variant_pk = f"{item['id']}:{variant['id']}"
                    existing_variant = MenuItemVariant.query.filter_by(id=variant_pk).first()
                    if existing_variant is None:
                        existing_variant = MenuItemVariant(
                            id=variant_pk,
                            menu_item_id=item["id"],
                            name=variant["name"],
                            price_minor=int(variant["cost"]),
                            weight=variant.get("weight"),
                            currency="USD",
                        )
                        db.session.add(existing_variant)
                    else:
                        existing_variant.name = variant["name"]
                        existing_variant.price_minor = int(variant["cost"])
                        existing_variant.weight = variant.get("weight")
        db.session.commit()


if __name__ == "__main__":
    run()
