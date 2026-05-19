import uuid
from types import SimpleNamespace

from app.services.admin_auth_service import AdminPrincipal
from app.services import admin_menu_service


def _actor() -> AdminPrincipal:
    return AdminPrincipal(
        telegram_user_id=1,
        restaurant_id="11111111-1111-1111-1111-111111111111",
        role="admin",
        username="owner",
    )


def test_create_menu_item_defaults_is_popular_false(monkeypatch):
    captured = []
    category = SimpleNamespace(id="cat-1", restaurant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"))

    class _CategoryQuery:
        def filter_by(self, **kwargs):
            return self

        def first(self):
            return category

    class _FakeCategoryModel:
        query = _CategoryQuery()

    monkeypatch.setattr(admin_menu_service, "MenuCategory", _FakeCategoryModel)
    monkeypatch.setattr(admin_menu_service.db.session, "add", lambda obj: captured.append(obj))

    item = admin_menu_service.create_menu_item(
        _actor(),
        {
            "name": "Lagman",
            "categoryId": "cat-1",
            "priceByCurrency": {"KZT": 2500},
            "variants": [{"name": "Default", "priceMinor": 2500, "currency": "KZT"}],
        },
    )

    assert item.is_popular is False
    assert captured[0].is_popular is False


def test_update_menu_item_updates_is_popular(monkeypatch):
    item = SimpleNamespace(
        id="item-1",
        restaurant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        is_popular=False,
    )

    class _ItemQuery:
        def filter_by(self, **kwargs):
            return self

        def first(self):
            return item

    class _FakeItemModel:
        query = _ItemQuery()

    monkeypatch.setattr(admin_menu_service, "MenuItem", _FakeItemModel)

    updated = admin_menu_service.update_menu_item(_actor(), "item-1", {"isPopular": True})
    assert updated.is_popular is True


def test_list_menu_items_includes_is_popular(monkeypatch):
    item = SimpleNamespace(
        id="item-1",
        category_id="cat-1",
        name="Lagman",
        name_i18n={"kk": "", "ru": "Лагман", "en": ""},
        description="",
        description_i18n={"kk": "", "ru": "", "en": ""},
        recipe=[],
        recipe_i18n={"kk": [], "ru": [], "en": []},
        image=None,
        price_by_currency={"KZT": 2500},
        discount_minor=0,
        discount_is_active=False,
        is_active=True,
        is_available_now=True,
        is_popular=True,
        created_at=0,
    )

    class _ItemsQuery:
        def filter_by(self, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return [item]

    class _VariantsQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return []

    class _FakeItemModel:
        query = _ItemsQuery()

    class _OrderColumn:
        def asc(self):
            return self

    _FakeItemModel.created_at = _OrderColumn()

    class _MenuItemIdColumn:
        def in_(self, values):
            return values

    class _FakeVariantModel:
        query = _VariantsQuery()
        menu_item_id = _MenuItemIdColumn()
        id = _OrderColumn()

    monkeypatch.setattr(admin_menu_service, "MenuItem", _FakeItemModel)
    monkeypatch.setattr(admin_menu_service, "MenuItemVariant", _FakeVariantModel)

    result = admin_menu_service.list_menu_items(_actor(), _actor().restaurant_id, None)
    assert result[0]["isPopular"] is True
