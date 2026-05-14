import json
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Order, OrderItem, OrderStatus, User


def _read_json(path: Path) -> list:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as infile:
        return json.load(infile)


def _write_json(path: Path, payload: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as outfile:
        json.dump(payload, outfile, ensure_ascii=False, indent=2)


def get_or_create_user(telegram_user_id: int, first_name: str | None, last_name: str | None, username: str | None) -> User:
    user = User.query.filter_by(telegram_user_id=telegram_user_id).first()
    if user is not None:
        return user

    user = User(
        telegram_user_id=telegram_user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )
    db.session.add(user)
    db.session.flush()
    return user


def persist_order(order_items: list[dict], telegram_user: dict, idempotency_key: str | None) -> str:
    if idempotency_key is not None:
        existing_order = Order.query.filter_by(idempotency_key=idempotency_key).first()
        if existing_order is not None:
            return str(existing_order.id)

    user = get_or_create_user(
        telegram_user_id=int(telegram_user["id"]),
        first_name=telegram_user.get("first_name"),
        last_name=telegram_user.get("last_name"),
        username=telegram_user.get("username"),
    )

    total_minor = 0
    order = Order(user_id=user.id, status=OrderStatus.pending_payment, currency="USD", idempotency_key=idempotency_key)
    db.session.add(order)
    db.session.flush()

    for item in order_items:
        quantity = int(item["quantity"])
        unit_minor = int(item["variant"]["cost"])
        line_total = quantity * unit_minor
        total_minor += line_total
        db.session.add(
            OrderItem(
                order_id=order.id,
                menu_item_id=item["cafeItem"].get("id"),
                item_name_snapshot=item["cafeItem"]["name"],
                variant_name_snapshot=item["variant"]["name"],
                unit_price_minor_snapshot=unit_minor,
                currency_snapshot="USD",
                quantity=quantity,
                line_total_minor=line_total,
            )
        )

    order.total_minor = total_minor
    try:
        db.session.commit()
        return str(order.id)
    except IntegrityError:
        db.session.rollback()
        if idempotency_key is not None:
            existing_order = Order.query.filter_by(idempotency_key=idempotency_key).first()
            if existing_order is not None:
                return str(existing_order.id)
        raise


def mirror_order_to_json(order_id: str, telegram_user: dict, order_items: list[dict], target_file: Path) -> None:
    payload = _read_json(target_file)
    payload.append(
        {
            "orderId": order_id,
            "telegramUserId": telegram_user.get("id"),
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "items": order_items,
        }
    )
    _write_json(target_file, payload)


def generate_idempotency_key(raw_key: str | None) -> str:
    return raw_key or str(uuid.uuid4())
