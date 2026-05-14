from app.services.admin_auth_service import AdminPrincipal
from app.services.admin_menu_service import resolve_restaurant_scope
from app.services.admin_staff_service import StaffPermissionError


def test_super_admin_cannot_manage_menu():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="11111111-1111-1111-1111-111111111111", role="super_admin", username="root")
    try:
        resolve_restaurant_scope(actor, None)
    except StaffPermissionError as exc:
        assert exc.status_code == 403
        return
    raise AssertionError("Expected StaffPermissionError")


def test_admin_cannot_use_other_restaurant_scope():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="11111111-1111-1111-1111-111111111111", role="admin", username="owner")
    try:
        resolve_restaurant_scope(actor, "22222222-2222-2222-2222-222222222222")
    except StaffPermissionError as exc:
        assert exc.status_code == 403
        return
    raise AssertionError("Expected StaffPermissionError")


def test_manager_uses_own_restaurant_scope_by_default():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="11111111-1111-1111-1111-111111111111", role="manager", username="manager")
    resolved = resolve_restaurant_scope(actor, None)
    assert str(resolved) == "11111111-1111-1111-1111-111111111111"
