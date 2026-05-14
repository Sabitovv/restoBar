from types import SimpleNamespace

from app import bot as bot_module
from app.services.admin_auth_service import AdminPrincipal


def test_start_sends_admin_button_for_staff(monkeypatch):
    calls = []

    monkeypatch.setattr(bot_module, "has_app_context", lambda: True)
    monkeypatch.setattr(
        bot_module,
        "resolve_active_membership",
        lambda _user_id, _username: AdminPrincipal(telegram_user_id=1, restaurant_id="r", role="admin", username="owner"),
    )
    monkeypatch.setattr(bot_module, "_effective_admin_app_url", lambda: "https://admin.restobar.su")
    monkeypatch.setattr(bot_module, "_send_webapp_button_message", lambda **kwargs: calls.append(kwargs))

    message = SimpleNamespace(chat=SimpleNamespace(id=100), from_user=SimpleNamespace(id=1, username="owner"))
    bot_module.send_role_based_start_message(message)

    assert calls
    assert calls[0]["button_label"] == "Open Admin"
    assert calls[0]["webapp_url"] == "https://admin.restobar.su"


def test_start_sends_menu_button_for_client(monkeypatch):
    calls = []

    monkeypatch.setattr(bot_module, "has_app_context", lambda: True)
    monkeypatch.setattr(bot_module, "resolve_active_membership", lambda _user_id, _username: None)
    monkeypatch.setattr(bot_module, "_effective_client_app_url", lambda: "https://miniapp.restobar.su")
    monkeypatch.setattr(bot_module, "_send_webapp_button_message", lambda **kwargs: calls.append(kwargs))

    message = SimpleNamespace(chat=SimpleNamespace(id=100), from_user=SimpleNamespace(id=2, username="guest"))
    bot_module.send_role_based_start_message(message)

    assert calls
    assert calls[0]["button_label"] == "Explore Menu"
    assert calls[0]["webapp_url"] == "https://miniapp.restobar.su"
