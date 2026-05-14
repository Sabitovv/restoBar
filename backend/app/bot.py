import logging
import os
import re
from typing import Any

import telebot
from flask import has_app_context
from telebot import TeleBot
from telebot.types import Update, WebAppInfo, Message
from telebot.util import quick_markup

from .observability.metrics import PAYMENTS_MARK_FAILED, PAYMENTS_MARKED_PAID
from .services.ai_service import AIService
from .services.admin_auth_service import resolve_active_membership
from .services.bot_message_service import save_ai_event, save_incoming_message, save_outgoing_message
from .services.prompt_builder import build_prompt
from .services.payment_service import mark_order_paid_from_telegram, order_exists_for_payload


logger = logging.getLogger(__name__)

BOT_TOKEN=os.getenv('BOT_TOKEN')
PAYMENT_PROVIDER_TOKEN=os.getenv('PAYMENT_PROVIDER_TOKEN')
WEBHOOK_URL=os.getenv('WEBHOOK_URL')
WEBHOOK_PATH='/bot'
APP_URL=os.getenv('APP_URL')

bot = TeleBot(BOT_TOKEN, parse_mode=None, threaded=False)
runtime: dict[str, Any] = {
    "queue": None,
    "settings": None,
    "app": None,
}


def configure_runtime(queue=None, settings=None, app=None):
    runtime["queue"] = queue
    runtime["settings"] = settings
    runtime["app"] = app


def _resolve_staff_principal(telegram_user_id: int, username: str | None):
    if has_app_context():
        return resolve_active_membership(telegram_user_id, username)

    app = runtime.get("app")
    if app is not None:
        with app.app_context():
            return resolve_active_membership(telegram_user_id, username)
    return None

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    """Message handler for messages containing 'successful_payment' field.
      This message is sent when the payment is successful and the payment flow is done.
      It's a good place to send the user a purchased item (if it is an electronic item, such as a key) 
      or to send a message that an item is on its way.

      The message param doesn't contain info about ordered good - they should be stored separately.
      Find more info: https://core.telegram.org/bots/api#successfulpayment.

      Example of Successful Payment message:
        {
            "update_id":12345,
            "message":{
                "message_id":12345,
                "date":1441645532,
                "chat":{
                    "last_name":"Doe",
                    "id":123456789,
                    "first_name":"John",
                    "username":"johndoe",
                    "type": ""
                },
                "successful_payment": {
                    "currency": "USD",
                    "total_amount": 1000,
                    "invoice_payload": "order_id",
                    "telegram_payment_charge_id": "12345",
                    "provider_payment_charge_id": "12345",
                    "order_info": {
                        "name": "John"
                    }
                }
            }
        }
    """
    user_name = message.successful_payment.order_info.name
    payment_result_text = ""
    if has_app_context():
        ok, result_text = mark_order_paid_from_telegram(message.successful_payment.to_dict())
        if not ok:
            PAYMENTS_MARK_FAILED.inc()
            payment_result_text = "\n\nPayment processing note: we are checking your payment status manually."
        else:
            PAYMENTS_MARKED_PAID.inc()
    else:
        payment_result_text = "\n\nPayment processing note: app context is not available."

    text = f'Thank you for your order, *{user_name}*! This is not a real cafe, so your card was not charged.\n\nHave a nice day 🙂'
    text += payment_result_text
    bot.send_message(
        chat_id=message.chat.id,
        text=text,
        parse_mode='markdown'
    )

@bot.pre_checkout_query_handler(func=lambda _: True)
def handle_pre_checkout_query(pre_checkout_query):
    """Here we may check if ordered items are still available.
      Since this is an example project, all the items are always in stock, so we answer query is OK.
      For other cases, when you perform a check and find out that you can't sell the items,
      you need to answer ok=False.
      Keep in mind: The check operation should not be longer than 10 seconds. If the Telegram API
      doesn't receive answer in 10 seconds, it cancels checkout.
    """
    payload = pre_checkout_query.invoice_payload
    is_ok = True
    error_message = None
    if has_app_context():
        is_ok = order_exists_for_payload(payload)
        if not is_ok:
            error_message = "Order was not found. Please try checkout again."
    bot.answer_pre_checkout_query(pre_checkout_query_id=pre_checkout_query.id, ok=is_ok, error_message=error_message)

@bot.message_handler(func=lambda message: re.match(r'/?start', message.text, re.IGNORECASE) is not None)
def handle_start_command(message):
    """Message handler for start messages, including '/start' command. This is an example how to
      use Regex for handling desired type of message. E.g. this handlers applies '/start', 
      '/START', 'start', 'START', 'sTaRt' and so on.
    """
    send_role_based_start_message(message)


@bot.message_handler(func=lambda message: re.match(r'/?admin', message.text, re.IGNORECASE) is not None)
def handle_admin_command(message):
    send_admin_access_message(message)

@bot.message_handler()
def handle_all_messages(message):
    """Fallback message handler that is invoced if none of above aren't match. This is a good
      practice to handle all the messages instead of ignoring unknown ones. In our case, we let user
      know that we can't handle the message and just advice to explore the menu using inline button.
    """
    settings = runtime.get("settings")
    user_payload = {
        "id": message.from_user.id,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
        "username": message.from_user.username,
    }
    conversation_id = None
    if has_app_context() and message.text is not None:
        conversation_id = save_incoming_message(user_payload, message.text)

    message_text = (message.text or "").strip()
    lower_message_text = message_text.lower()
    if lower_message_text and any(keyword in lower_message_text for keyword in ["menu", "меню", "еда", "кушать", "food"]):
        send_actionable_message(
            chat_id=message.chat.id,
            text="Great choice. Tap *Explore Menu* to open the Mini App and see all categories.",
        )
        return

    if settings is not None and settings.enable_ai_bot_replies and message.text is not None:
        queue = runtime.get("queue")
        if queue is not None and has_app_context():
            queue.enqueue(
                "app.workers.ai_tasks.process_ai_message_task",
                message_text=message.text,
                context_messages=[],
                menu_facts=[],
                model=settings.ai_model,
                timeout_seconds=settings.ai_request_timeout_seconds,
                max_retries=settings.ai_max_retries,
            )
            bot.send_message(chat_id=message.chat.id, text="Got it. Thinking about your question...")
            return

        ai_service = AIService(
            model=settings.ai_model,
            timeout_seconds=settings.ai_request_timeout_seconds,
            max_retries=settings.ai_max_retries,
        )
        prompt = build_prompt(message.text, context_messages=[], menu_facts=[])
        result = ai_service.generate_reply(prompt)
        if result.get("ok"):
            answer = result["content"]
            bot.send_message(chat_id=message.chat.id, text=answer)
            if conversation_id is not None and has_app_context():
                save_outgoing_message(
                    conversation_id=conversation_id,
                    content=answer,
                    model=result.get("model") or settings.ai_model,
                    token_in=result.get("token_in"),
                    token_out=result.get("token_out"),
                    latency_ms=result.get("latency_ms"),
                )
            return

        fallback = result.get("fallback") or "Sorry, I cannot answer now."
        bot.send_message(chat_id=message.chat.id, text=fallback)
        if has_app_context():
            save_ai_event(conversation_id, "ai_generation_failed", "error", result)
        return

    send_actionable_message(chat_id=message.chat.id, text="To be honest, I don't know how to reply to messages. But I can offer you to familiarize yourself with our menu. I am sure you will find something to your liking! 😉")

def send_actionable_message(chat_id, text):
    """Method allows to send the text to the chat and attach inline button to it.
      Inline button will open our Mini App on click.
    """
    app_url = _effective_client_app_url()
    if app_url and app_url.startswith("https://"):
        markup = quick_markup({
            'Explore Menu': {
                'web_app': WebAppInfo(app_url)
            },
        }, row_width=1)
        bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='markdown',
            reply_markup=markup
        )
        return

    bot.send_message(
        chat_id=chat_id,
        text=(
            f"{text}\n\n"
            "Mini App button is disabled in local polling mode because Telegram accepts only HTTPS Web App URLs. "
            "Use webhook mode with a public HTTPS URL to open the Mini App button."
        ),
        parse_mode='markdown',
    )


def _effective_client_app_url() -> str | None:
    settings = runtime.get("settings")
    if settings is not None and getattr(settings, "app_url", None):
        return settings.app_url
    return APP_URL


def _effective_admin_app_url() -> str | None:
    settings = runtime.get("settings")
    if settings is not None and getattr(settings, "admin_app_url", None):
        return settings.admin_app_url
    return os.getenv("ADMIN_APP_URL")


def _send_webapp_button_message(chat_id: int, text: str, button_label: str, webapp_url: str | None):
    if webapp_url and webapp_url.startswith("https://"):
        markup = quick_markup(
            {
                button_label: {
                    "web_app": WebAppInfo(webapp_url)
                }
            },
            row_width=1,
        )
        bot.send_message(chat_id=chat_id, text=text, parse_mode="markdown", reply_markup=markup)
        return

    bot.send_message(
        chat_id=chat_id,
        text=(
            f"{text}\n\n"
            "Mini App button is disabled because Telegram accepts only HTTPS Web App URLs. "
            "Configure a public HTTPS URL and try again."
        ),
        parse_mode="markdown",
    )


def send_role_based_start_message(message):
    principal = _resolve_staff_principal(message.from_user.id, message.from_user.username)
    if principal is not None:
        _send_webapp_button_message(
            chat_id=message.chat.id,
            text="*Welcome back!* You have staff access. Open the admin panel to manage restaurants, menu and staff.",
            button_label="Open Admin",
            webapp_url=_effective_admin_app_url(),
        )
        return

    _send_webapp_button_message(
        chat_id=message.chat.id,
        text="*Welcome to Laurel Cafe!* 🌿\n\nIt is time to order something delicious 😋 Tap the button below to get started.",
        button_label="Explore Menu",
        webapp_url=_effective_client_app_url(),
    )


def send_admin_access_message(message):
    principal = _resolve_staff_principal(message.from_user.id, message.from_user.username)
    if principal is None:
        bot.send_message(chat_id=message.chat.id, text="Access denied. Admin panel is available only for approved staff users.")
        return

    _send_webapp_button_message(
        chat_id=message.chat.id,
        text="Open the admin panel:",
        button_label="Open Admin",
        webapp_url=_effective_admin_app_url(),
    )

def refresh_webhook():
    """Just a wrapper for remove & set webhook ops"""
    if not BOT_TOKEN:
        logger.warning("Skipping webhook refresh: BOT_TOKEN is not set")
        return
    if not WEBHOOK_URL or not WEBHOOK_URL.startswith("https://"):
        logger.warning("Skipping webhook refresh: WEBHOOK_URL is empty or not HTTPS")
        return
    try:
        bot.remove_webhook()
        bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
    except Exception as exc:
        logger.exception("Webhook refresh failed: %s", exc)


def run_polling():
    if not BOT_TOKEN or BOT_TOKEN.strip() == "replace_with_bot_token":
        logger.error("Cannot start polling: set a real BOT_TOKEN in backend/.env")
        return
    logger.info("Starting Telegram bot in polling mode")
    try:
        bot.remove_webhook()
    except Exception as exc:
        logger.warning("remove_webhook failed before polling start: %s", exc)
    bot.infinity_polling(skip_pending=True)

def process_update(update_json):
    """Pass received Update JSON to the Bot for processing.
      This method should be typically called from the webhook method.
      
    Args:
        update_json: Update object sent from the Telegram API. See https://core.telegram.org/bots/api#update.
    """
    update = Update.de_json(update_json)
    bot.process_new_updates([update])

def create_invoice_link(prices, payload: str = 'orderID') -> str:
    """Just a handy wrapper for creating an invoice link for payment. Since this is an example project,
      most of the fields are hardcode.
    """
    return bot.create_invoice_link(
        title='Order #1',
        description='Great choice! Last steps and we will get to cooking ;)',
        payload=payload,
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency='USD',
        prices=prices,
        need_name=True,
        need_phone_number=True,
        need_shipping_address=True
    )

def enable_debug_logging():
    """Display all logs from the Bot. May be useful while developing."""
    telebot.logger.setLevel(logging.DEBUG)
