from types import SimpleNamespace

from app.services.admin_auth_service import AdminPrincipal
from app.services.admin_restaurant_service import create_restaurant, delete_restaurant
from app.services.admin_staff_service import StaffPermissionError


def test_create_restaurant_requires_super_admin():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="11111111-1111-1111-1111-111111111111", role="admin", username="owner")
    try:
        create_restaurant(actor, {"name": "Resto", "slug": "resto"})
    except StaffPermissionError as exc:
        assert exc.status_code == 403
        return
    raise AssertionError("Expected StaffPermissionError")


def test_create_restaurant_rejects_duplicate_slug(monkeypatch):
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="11111111-1111-1111-1111-111111111111", role="super_admin", username="root")

    class FakeQuery:
        @staticmethod
        def filter_by(**_kwargs):
            return SimpleNamespace(first=lambda: object())

    from app.services import admin_restaurant_service

    monkeypatch.setattr(admin_restaurant_service, "Restaurant", SimpleNamespace(query=FakeQuery))
    try:
        create_restaurant(actor, {"name": "Resto", "slug": "resto"})
    except StaffPermissionError as exc:
        assert exc.status_code == 409
        return
    raise AssertionError("Expected StaffPermissionError")


def test_delete_restaurant_requires_super_admin():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="11111111-1111-1111-1111-111111111111", role="admin", username="owner")
    try:
        delete_restaurant(actor, "11111111-1111-1111-1111-111111111111")
    except StaffPermissionError as exc:
        assert exc.status_code == 403
        return
    raise AssertionError("Expected StaffPermissionError")
