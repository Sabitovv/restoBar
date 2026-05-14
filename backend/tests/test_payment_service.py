from app.services.payment_service import order_exists_for_payload


def test_order_exists_for_payload_rejects_legacy_payload():
    assert not order_exists_for_payload("orderID")


def test_order_exists_for_payload_rejects_malformed_uuid():
    assert not order_exists_for_payload("not-a-uuid")
