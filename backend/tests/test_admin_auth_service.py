from app.services.admin_auth_service import AdminPrincipal, issue_admin_session, read_admin_session


def test_issue_and_read_admin_session_roundtrip():
    principal = AdminPrincipal(telegram_user_id=42, restaurant_id="rest-1", role="admin", username="owner")
    token = issue_admin_session("secret", principal)
    restored = read_admin_session("secret", token)
    assert restored is not None
    assert restored.telegram_user_id == 42
    assert restored.restaurant_id == "rest-1"
    assert restored.role == "admin"


def test_read_admin_session_rejects_invalid_signature():
    principal = AdminPrincipal(telegram_user_id=42, restaurant_id="rest-1", role="admin", username="owner")
    token = issue_admin_session("secret", principal)
    assert read_admin_session("other-secret", token) is None
