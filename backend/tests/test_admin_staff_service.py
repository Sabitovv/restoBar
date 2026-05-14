from types import SimpleNamespace

from app.services.admin_auth_service import AdminPrincipal
from app.models import StaffRole
from app.services.admin_staff_service import StaffPermissionError, assert_role_change_allowed, change_staff_role, invite_staff_member


def test_admin_cannot_assign_admin_role():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="r1", role="admin", username="owner")
    try:
        assert_role_change_allowed(actor, target_role="admin")
    except StaffPermissionError as exc:
        assert exc.status_code == 403
        return
    raise AssertionError("Expected StaffPermissionError")


def test_admin_can_assign_manager_role():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="r1", role="admin", username="owner")
    assert_role_change_allowed(actor, target_role="manager")


def test_super_admin_can_assign_admin_role():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="r1", role="super_admin", username="root")
    assert_role_change_allowed(actor, target_role="admin")


def test_super_admin_cannot_assign_manager_role():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="r1", role="super_admin", username="root")
    try:
        assert_role_change_allowed(actor, target_role="manager")
    except StaffPermissionError as exc:
        assert exc.status_code == 403
        return
    raise AssertionError("Expected StaffPermissionError")


def test_invalid_role_returns_validation_error():
    actor = AdminPrincipal(telegram_user_id=1, restaurant_id="r1", role="super_admin", username="root")
    try:
        assert_role_change_allowed(actor, target_role="bad-role")
    except StaffPermissionError as exc:
        assert exc.status_code == 400
        return
    raise AssertionError("Expected StaffPermissionError")


def test_super_admin_cannot_self_demote(monkeypatch):
    actor = AdminPrincipal(
        telegram_user_id=42,
        restaurant_id="11111111-1111-1111-1111-111111111111",
        role="super_admin",
        username="root",
    )

    class FakeQuery:
        @staticmethod
        def filter_by(**_kwargs):
            class Result:
                @staticmethod
                def first():
                    class Membership:
                        role = StaffRole.super_admin
                        telegram_user_id = 42
                        restaurant_id = actor.restaurant_id

                    return Membership()

            return Result()

    from app.services import admin_staff_service

    monkeypatch.setattr(admin_staff_service, "StaffMembership", SimpleNamespace(query=FakeQuery))
    try:
        change_staff_role(actor, "11111111-1111-1111-1111-111111111111", "manager")
    except StaffPermissionError as exc:
        assert exc.status_code == 403
        return
    raise AssertionError("Expected StaffPermissionError")


def test_super_admin_inviting_admin_requires_restaurant_id():
    actor = AdminPrincipal(
        telegram_user_id=42,
        restaurant_id="11111111-1111-1111-1111-111111111111",
        role="super_admin",
        username="root",
    )

    try:
        invite_staff_member(
            actor,
            {
                "role": "admin",
                "username": "newowner",
            },
        )
    except StaffPermissionError as exc:
        assert exc.status_code == 400
        return
    raise AssertionError("Expected StaffPermissionError")
