from datetime import datetime

from ..extensions import db
from ..models import AIEvent, BotConversation, BotMessage, User


def _get_or_create_user(telegram_user: dict) -> User:
    user = User.query.filter_by(telegram_user_id=int(telegram_user["id"])).first()
    if user is None:
        user = User(
            telegram_user_id=int(telegram_user["id"]),
            first_name=telegram_user.get("first_name"),
            last_name=telegram_user.get("last_name"),
            username=telegram_user.get("username"),
        )
        db.session.add(user)
        db.session.flush()
    return user


def _get_or_create_active_conversation(user_id):
    conversation = BotConversation.query.filter_by(user_id=user_id, state="active").first()
    if conversation is None:
        conversation = BotConversation(user_id=user_id, state="active")
        db.session.add(conversation)
        db.session.flush()
    conversation.last_message_at = datetime.utcnow()
    return conversation


def save_incoming_message(telegram_user: dict, content: str) -> str:
    user = _get_or_create_user(telegram_user)
    conversation = _get_or_create_active_conversation(user.id)
    message = BotMessage(conversation_id=conversation.id, role="user", content=content)
    db.session.add(message)
    db.session.commit()
    return str(conversation.id)


def save_outgoing_message(conversation_id: str, content: str, model: str, token_in: int | None, token_out: int | None, latency_ms: int | None) -> None:
    message = BotMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=content,
        model=model,
        token_in=token_in,
        token_out=token_out,
        latency_ms=latency_ms,
    )
    db.session.add(message)
    db.session.commit()


def save_ai_event(conversation_id: str | None, event_type: str, severity: str, payload_json: dict | None = None) -> None:
    event = AIEvent(conversation_id=conversation_id, event_type=event_type, severity=severity, payload_json=payload_json)
    db.session.add(event)
    db.session.commit()
