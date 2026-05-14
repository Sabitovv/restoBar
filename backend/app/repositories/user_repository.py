from sqlalchemy import select

from ..extensions import db
from ..models import User


def get_user_by_telegram_id(telegram_user_id: int):
    return db.session.execute(select(User).where(User.telegram_user_id == telegram_user_id)).scalar_one_or_none()
