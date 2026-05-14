from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ..extensions import db
from ..models import MembershipStatus, StaffMembership, StaffRole
from .admin_auth_service import AdminPrincipal


@dataclass
class StaffPermissionError(Exception):
    message: str
    status_code: int


def _role_value(role: str) -> StaffRole:
    try:
        return StaffRole(role)
    except ValueError as exc:
        raise StaffPermissionError("Unsupported role.", 400) from exc


def _normalize_username(username: str | None) -> str | None:
    if username is None:
        return None
    value = username.strip().lstrip("@").lower()
    return value or None


def assert_role_change_allowed(actor: AdminPrincipal, target_role: StaffRole | str) -> None:
    if isinstance(target_role, str):
        target_role = _role_value(target_role)
    if actor.role == StaffRole.super_admin.value:
        if target_role != StaffRole.admin:
            raise StaffPermissionError("Super admin can assign only admin role.", 403)
        return
    if actor.role == StaffRole.admin.value and target_role == StaffRole.manager:
        return
    raise StaffPermissionError("Insufficient permissions for target role.", 403)


def list_staff(restaurant_id: str, include_revoked: bool = False) -> list[dict]:
    query = StaffMembership.query.filter_by(restaurant_id=UUID(restaurant_id))
    if not include_revoked:
        query = query.filter(StaffMembership.status != MembershipStatus.revoked)
    members = query.order_by(StaffMembership.created_at.asc()).all()
    return [
        {
            "id": str(member.id),
            "restaurantId": str(member.restaurant_id),
            "telegramUserId": member.telegram_user_id,
            "username": member.username,
            "phoneNumber": member.phone_number,
            "role": member.role.value,
            "status": member.status.value,
        }
        for member in members
    ]


def invite_staff_member(actor: AdminPrincipal, payload: dict) -> StaffMembership:
    role = _role_value(payload.get("role", ""))
    assert_role_change_allowed(actor, role)

    desired_restaurant_id = payload.get("restaurantId") or actor.restaurant_id
    if actor.role == StaffRole.super_admin.value and role == StaffRole.admin and not payload.get("restaurantId"):
        raise StaffPermissionError("restaurantId is required when assigning admin role.", 400)
    if actor.role != StaffRole.super_admin.value and desired_restaurant_id != actor.restaurant_id:
        raise StaffPermissionError("Admin can invite only in own restaurant.", 403)

    telegram_user_id = payload.get("telegramUserId")
    username = _normalize_username(payload.get("username"))
    phone_number = payload.get("phoneNumber")
    if telegram_user_id is None and username is None and phone_number is None:
        raise StaffPermissionError("Provide telegramUserId, username, or phoneNumber.", 400)

    query = StaffMembership.query.filter_by(restaurant_id=UUID(desired_restaurant_id))
    if telegram_user_id is not None:
        query = query.filter_by(telegram_user_id=int(telegram_user_id))
    elif username is not None:
        query = query.filter(db.func.lower(StaffMembership.username) == username)
    else:
        query = query.filter_by(phone_number=phone_number)
    membership = query.first()

    if membership is None:
        membership = StaffMembership(
            restaurant_id=UUID(desired_restaurant_id),
            telegram_user_id=int(telegram_user_id) if telegram_user_id is not None else None,
            username=username,
            phone_number=phone_number,
            role=role,
            status=MembershipStatus.invited,
        )
        db.session.add(membership)
    else:
        membership.username = username or membership.username
        membership.phone_number = phone_number or membership.phone_number
        membership.role = role
        membership.status = MembershipStatus.invited
        if telegram_user_id is not None:
            membership.telegram_user_id = int(telegram_user_id)

    return membership


def revoke_staff_member(actor: AdminPrincipal, membership_id: str) -> StaffMembership:
    membership = StaffMembership.query.filter_by(id=UUID(membership_id)).first()
    if membership is None:
        raise StaffPermissionError("Membership not found.", 404)
    if actor.role != StaffRole.super_admin.value and str(membership.restaurant_id) != actor.restaurant_id:
        raise StaffPermissionError("Cannot revoke out-of-scope membership.", 403)
    if membership.role == StaffRole.super_admin and actor.role != StaffRole.super_admin.value:
        raise StaffPermissionError("Cannot revoke super admin membership.", 403)
    if actor.role == StaffRole.super_admin.value and membership.telegram_user_id == actor.telegram_user_id:
        raise StaffPermissionError("Self-revoke is not allowed for super admin.", 403)
    assert_role_change_allowed(actor, membership.role)
    membership.status = MembershipStatus.revoked
    return membership


def change_staff_role(actor: AdminPrincipal, membership_id: str, role: str) -> StaffMembership:
    membership = StaffMembership.query.filter_by(id=UUID(membership_id)).first()
    if membership is None:
        raise StaffPermissionError("Membership not found.", 404)
    if actor.role != StaffRole.super_admin.value and str(membership.restaurant_id) != actor.restaurant_id:
        raise StaffPermissionError("Cannot modify out-of-scope membership.", 403)

    target_role = _role_value(role)
    if membership.role == StaffRole.super_admin and actor.role != StaffRole.super_admin.value:
        raise StaffPermissionError("Cannot modify super admin role.", 403)
    if actor.role == StaffRole.super_admin.value and membership.telegram_user_id == actor.telegram_user_id and target_role != StaffRole.super_admin:
        raise StaffPermissionError("Self-demotion is not allowed for super admin.", 403)
    assert_role_change_allowed(actor, target_role)
    membership.role = target_role
    if membership.status == MembershipStatus.revoked:
        membership.status = MembershipStatus.active
    return membership
