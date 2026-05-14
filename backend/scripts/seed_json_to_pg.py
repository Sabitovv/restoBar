import json
from pathlib import Path

from app.main import app
from app.extensions import db
from app.models import CafeInfo, MenuCategory, MenuItem, MenuItemVariant


def run() -> None:
    base = Path(__file__).resolve().parents[1] / "data"
    with app.app_context():
        info_payload = json.loads((base / "info.json").read_text(encoding="utf-8"))
        existing_info = CafeInfo.query.filter_by(id="main").first()
        if existing_info is None:
            db.session.add(CafeInfo(id="main", payload_json=info_payload))
        else:
            existing_info.payload_json = info_payload

        categories = json.loads((base / "categories.json").read_text(encoding="utf-8"))
        for category in categories:
            if not MenuCategory.query.filter_by(id=category["id"]).first():
                db.session.add(MenuCategory(id=category["id"], name=category["name"]))

        for menu_file in (base / "menu").glob("*.json"):
            menu_items = json.loads(menu_file.read_text(encoding="utf-8"))
            category_id = menu_file.stem
            for item in menu_items:
                if not MenuItem.query.filter_by(id=item["id"]).first():
                    db.session.add(
                        MenuItem(
                            id=item["id"],
                            category_id=category_id,
                            name=item["name"],
                            description=item.get("description"),
                            image=item.get("image"),
                        )
                    )
                for variant in item.get("variants", []):
                    variant_pk = f"{item['id']}:{variant['id']}"
                    if not MenuItemVariant.query.filter_by(id=variant_pk).first():
                        db.session.add(
                            MenuItemVariant(
                                id=variant_pk,
                                menu_item_id=item["id"],
                                name=variant["name"],
                                price_minor=int(variant["cost"]),
                                currency="USD",
                            )
                        )
        db.session.commit()


if __name__ == "__main__":
    run()
