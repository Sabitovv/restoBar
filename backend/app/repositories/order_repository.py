from sqlalchemy import select

from ..extensions import db
from ..models import Order


def get_order_by_id(order_id):
    return db.session.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
