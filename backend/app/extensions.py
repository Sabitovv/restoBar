from flask_sqlalchemy import SQLAlchemy
from redis import Redis
from rq import Queue


db = SQLAlchemy()


def build_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(redis_url, decode_responses=True)


def build_queue(redis_client: Redis, queue_name: str = "ai") -> Queue:
    return Queue(queue_name, connection=redis_client)
