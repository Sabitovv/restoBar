import hashlib
import hmac
import time

from app.auth import parse_auth_data, validate_auth_data, validate_telegram_login_payload


def _sign_auth_data(bot_token: str, payload: dict) -> str:
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(key=b"WebAppData", msg=bot_token.encode(), digestmod=hashlib.sha256)
    payload_hash = hmac.new(key=secret_key.digest(), msg=data_check_string.encode(), digestmod=hashlib.sha256).hexdigest()
    encoded = "&".join([f"{k}={v}" for k, v in payload.items()])
    return f"{encoded}&hash={payload_hash}"


def test_validate_auth_data_accepts_valid_fresh_payload():
    bot_token = "test_token"
    payload = {
        "auth_date": str(int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": '{"id":42,"first_name":"T"}',
    }
    auth_data = _sign_auth_data(bot_token, payload)
    assert validate_auth_data(bot_token, auth_data, max_age_seconds=300)


def test_validate_auth_data_rejects_expired_payload():
    bot_token = "test_token"
    payload = {
        "auth_date": str(int(time.time()) - 1000),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": '{"id":42,"first_name":"T"}',
    }
    auth_data = _sign_auth_data(bot_token, payload)
    assert not validate_auth_data(bot_token, auth_data, max_age_seconds=300)


def test_parse_auth_data_extracts_user_json():
    auth_data = "auth_date=1700000000&query_id=x1&user=%7B%22id%22%3A42%7D&hash=test"
    parsed = parse_auth_data(auth_data)
    assert parsed is not None
    assert parsed["user"]["id"] == 42


def _sign_telegram_login_payload(bot_token: str, payload: dict) -> dict:
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    payload_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    signed = dict(payload)
    signed["hash"] = payload_hash
    return signed


def test_validate_telegram_login_payload_accepts_valid_payload():
    bot_token = "test_token"
    payload = {
        "id": "42",
        "username": "owner",
        "first_name": "Test",
        "auth_date": str(int(time.time())),
    }
    signed = _sign_telegram_login_payload(bot_token, payload)
    assert validate_telegram_login_payload(bot_token, signed, max_age_seconds=300)


def test_validate_telegram_login_payload_rejects_tampered_payload():
    bot_token = "test_token"
    payload = {
        "id": "42",
        "username": "owner",
        "first_name": "Test",
        "auth_date": str(int(time.time())),
    }
    signed = _sign_telegram_login_payload(bot_token, payload)
    signed["username"] = "other"
    assert not validate_telegram_login_payload(bot_token, signed, max_age_seconds=300)
