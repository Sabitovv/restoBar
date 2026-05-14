from app.main import app
from app.models import CafeInfo, MenuCategory, MenuItem, MenuItemVariant, Order


def run() -> None:
    with app.app_context():
        print(f"menu_categories={MenuCategory.query.count()}")
        print(f"menu_items={MenuItem.query.count()}")
        print(f"menu_item_variants={MenuItemVariant.query.count()}")
        print(f"cafe_info={CafeInfo.query.count()}")
        print(f"orders={Order.query.count()}")


if __name__ == "__main__":
    run()
