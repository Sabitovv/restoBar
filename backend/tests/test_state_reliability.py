import uuid
from types import SimpleNamespace

from app.models import OrderStatus
from app.services import payment_service, storage_service


def test_persist_order_returns_existing_order_by_idempotency_key(monkeypatch):
    order_id = uuid.uuid4()

    class ExistingQuery:
        @staticmethod
        def filter_by(**kwargs):
            assert kwargs.get("idempotency_key") == "same-key"
            return SimpleNamespace(first=lambda: SimpleNamespace(id=order_id))

    class DummyOrder:
        query = ExistingQuery

    monkeypatch.setattr(storage_service, "Order", DummyOrder)

    result = storage_service.persist_order(
        order_items=[],
        telegram_user={"id": 1, "first_name": "N", "last_name": None, "username": None},
        idempotency_key="same-key",
    )
    assert result == str(order_id)


def test_mark_order_paid_returns_success_if_already_paid(monkeypatch):
    paid_order = SimpleNamespace(id=uuid.uuid4(), status=OrderStatus.paid)

    class DummyExecuteResult:
        @staticmethod
        def scalar_one_or_none():
            return paid_order

    monkeypatch.setattr(payment_service.db.session, "execute", lambda *_args, **_kwargs: DummyExecuteResult())

    ok, message = payment_service.mark_order_paid_from_telegram(
        {
            "invoice_payload": str(paid_order.id),
            "provider_payment_charge_id": "provider-1",
            "telegram_payment_charge_id": "telegram-1",
            "total_amount": 100,
            "currency": "USD",
        }
    )

    assert ok is True
    assert message == "Order already marked as paid"
