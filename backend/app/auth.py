import hashlib
import hmac
import json
import time
from operator import itemgetter
from urllib.parse import parse_qsl


def _telegram_secret_key(bot_token: str) -> bytes:
    return hashlib.sha256(bot_token.encode()).digest()

def validate_auth_data(bot_token: str, auth_data: str, max_age_seconds: int = 300) -> bool:
    """Validates initData from the Telegram Mini App.
    You can find more info here: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app.

    Args:
      bot_token: The token you received (will receive) when creating a bot in BotFather.
      auth_data: Chain of all received fields, sorted alphabetically, in the format key=<value> 
        with a line feed character ('\\n', 0x0A) used as separator - 
        e.g., 'auth_date=<auth_date>\\nquery_id=<query_id>\\nuser=<user>'.

    Returns:
      True if the provided auth_data valid, False otherwise.
    """
    try:
        parsed_data = dict(parse_qsl(auth_data, strict_parsing=True))
    except ValueError:
        return False
    
    if "hash" not in parsed_data:
        return False
    hash_ = parsed_data.pop("hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items(), key=itemgetter(0))
    )
    secret_key = hmac.new(key=b"WebAppData", msg=bot_token.encode(), digestmod=hashlib.sha256)
    calculated_hash = hmac.new(
        key=secret_key.digest(),
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, hash_):
        return False

    auth_date = parsed_data.get("auth_date")
    if auth_date is None:
        return False

    try:
        auth_date_ts = int(auth_date)
    except ValueError:
        return False

    now_ts = int(time.time())
    if now_ts - auth_date_ts > max_age_seconds:
        return False

    return True


def parse_auth_data(auth_data: str) -> dict | None:
    try:
        parsed_data = dict(parse_qsl(auth_data, strict_parsing=True))
    except ValueError:
        return None

    if "user" in parsed_data:
        try:
            parsed_data["user"] = json.loads(parsed_data["user"])
        except json.JSONDecodeError:
            return None

    return parsed_data


def validate_telegram_login_payload(bot_token: str, payload: dict, max_age_seconds: int = 300) -> bool:
    if not bot_token or not payload:
        return False
    payload_hash = payload.get("hash")
    auth_date = payload.get("auth_date")
    if payload_hash is None or auth_date is None:
        return False

    login_payload = {k: v for k, v in payload.items() if k != "hash" and v is not None}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(login_payload.items(), key=itemgetter(0)))
    calculated_hash = hmac.new(
        key=_telegram_secret_key(bot_token),
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, str(payload_hash)):
        return False

    try:
        auth_date_ts = int(str(auth_date))
    except ValueError:
        return False

    now_ts = int(time.time())
    if now_ts - auth_date_ts > max_age_seconds:
        return False
    return True
