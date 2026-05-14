import hashlib
import json

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import ProcessedUpdate


def register_telegram_update(update_id: int, payload: dict) -> bool:
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    processed_update = ProcessedUpdate(update_id=update_id, payload_hash=payload_hash)
    db.session.add(processed_update)
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False
