import secrets

from redis import Redis


def acquire_user_lock(redis_client: Redis, telegram_user_id: int, ttl_seconds: int = 15) -> str | None:
    key = f"lock:user:{telegram_user_id}"
    token = secrets.token_urlsafe(12)
    locked = redis_client.set(key, token, nx=True, ex=ttl_seconds)
    if not locked:
        return None
    return token


def release_user_lock(redis_client: Redis, telegram_user_id: int, token: str) -> bool:
    key = f"lock:user:{telegram_user_id}"
    current_token = redis_client.get(key)
    if current_token != token:
        return False
    redis_client.delete(key)
    return True
