from __future__ import annotations

from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..extensions import db
from ..models import MembershipStatus, StaffMembership, User


@dataclass
class AdminPrincipal:
    telegram_user_id: int
    restaurant_id: str
    role: str
    username: str | None


def _to_principal(membership: StaffMembership) -> AdminPrincipal:
    return AdminPrincipal(
        telegram_user_id=membership.telegram_user_id,
        restaurant_id=str(membership.restaurant_id),
        role=membership.role.value,
        username=membership.username,
    )


def resolve_active_membership(telegram_user_id: int, username: str | None) -> AdminPrincipal | None:
    membership = (
        StaffMembership.query.filter_by(telegram_user_id=telegram_user_id, status=MembershipStatus.active)
        .order_by(StaffMembership.created_at.asc())
        .first()
    )
    if membership is not None:
        return _to_principal(membership)

    if not username:
        return None

    normalized_username = username.lstrip("@").lower()
    invited_membership = (
        StaffMembership.query.filter(
            db.func.lower(StaffMembership.username) == normalized_username,
            StaffMembership.status.in_([MembershipStatus.invited, MembershipStatus.active]),
        )
        .order_by(StaffMembership.created_at.asc())
        .first()
    )
    if invited_membership is None:
        return None

    invited_membership.telegram_user_id = telegram_user_id
    invited_membership.username = normalized_username
    invited_membership.status = MembershipStatus.active
    db.session.commit()
    return _to_principal(invited_membership)


def upsert_user_from_telegram(telegram_user_id: int, first_name: str | None, last_name: str | None, username: str | None) -> User:
    user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
    if user is None:
        user = User(
            telegram_user_id=telegram_user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        return user

    user.first_name = first_name
    user.last_name = last_name
    user.username = username
    return user


def issue_admin_session(secret: str, principal: AdminPrincipal) -> str:
    serializer = URLSafeTimedSerializer(secret)
    return serializer.dumps(
        {
            "telegram_user_id": principal.telegram_user_id,
            "restaurant_id": principal.restaurant_id,
            "role": principal.role,
        }
    )


def read_admin_session(secret: str, token: str, max_age_seconds: int = 60 * 60 * 12) -> AdminPrincipal | None:
    serializer = URLSafeTimedSerializer(secret)
    try:
        payload = serializer.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None

    telegram_user_id = payload.get("telegram_user_id")
    restaurant_id = payload.get("restaurant_id")
    role = payload.get("role")
    if telegram_user_id is None or restaurant_id is None or role is None:
        return None
    return AdminPrincipal(
        telegram_user_id=int(telegram_user_id),
        restaurant_id=str(restaurant_id),
        role=str(role),
        username=None,
    )


def get_active_staff_membership(telegram_user_id: int) -> AdminPrincipal | None:
    membership = (
        StaffMembership.query.filter_by(telegram_user_id=telegram_user_id, status=MembershipStatus.active)
        .order_by(StaffMembership.created_at.asc())
        .first()
    )
    if membership is None:
        return None
    return _to_principal(membership)
