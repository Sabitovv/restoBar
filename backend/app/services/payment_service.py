import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Order, OrderStatus, Payment


def order_exists_for_payload(invoice_payload: str) -> bool:
    if not invoice_payload or invoice_payload == "orderID":
        return False
    try:
        order_id = uuid.UUID(invoice_payload)
    except ValueError:
        return False
    order = db.session.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    ).scalar_one_or_none()
    return order is not None


def mark_order_paid_from_telegram(successful_payment: dict) -> tuple[bool, str]:
    invoice_payload = successful_payment.get("invoice_payload")
    provider_payment_id = successful_payment.get("provider_payment_charge_id")
    telegram_payment_id = successful_payment.get("telegram_payment_charge_id")
    amount_minor = int(successful_payment.get("total_amount", 0))
    currency = successful_payment.get("currency", "USD")

    if not invoice_payload or invoice_payload == "orderID":
        return False, "Order payload is missing"

    if provider_payment_id is None:
        return False, "Provider payment id is missing"

    try:
        order_id = uuid.UUID(invoice_payload)
    except ValueError:
        return False, "Order payload is malformed"

    order = db.session.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order is None:
        return False, "Order not found"

    if order.status == OrderStatus.paid:
        return True, "Order already marked as paid"

    payload_hash = hashlib.sha256(json.dumps(successful_payment, sort_keys=True).encode()).hexdigest()
    payment = Payment(
        order_id=order.id,
        provider="telegram",
        provider_payment_id=provider_payment_id,
        status="succeeded",
        amount_minor=amount_minor,
        currency=currency,
        provider_payload_hash=payload_hash,
        idempotency_key=telegram_payment_id or provider_payment_id,
    )

    db.session.add(payment)
    order.status = OrderStatus.paid

    try:
        db.session.commit()
        return True, "Order marked as paid"
    except IntegrityError:
        db.session.rollback()
        existing_payment = Payment.query.filter_by(provider_payment_id=provider_payment_id).first()
        if existing_payment is not None:
            if order.status != OrderStatus.paid:
                order.status = OrderStatus.paid
                db.session.commit()
            return True, "Payment already registered"
        return False, "Failed to persist payment"
