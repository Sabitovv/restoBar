from app.services.lock_service import acquire_user_lock, release_user_lock


class FakeRedis:
    def __init__(self):
        self.data = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    def get(self, key):
        return self.data.get(key)

    def delete(self, key):
        self.data.pop(key, None)


def test_acquire_user_lock_returns_none_if_already_locked():
    redis_client = FakeRedis()
    token = acquire_user_lock(redis_client, 123)
    assert token is not None
    second_token = acquire_user_lock(redis_client, 123)
    assert second_token is None


def test_release_user_lock_checks_token():
    redis_client = FakeRedis()
    token = acquire_user_lock(redis_client, 123)
    assert token is not None
    assert not release_user_lock(redis_client, 123, "wrong")
    assert release_user_lock(redis_client, 123, token)
