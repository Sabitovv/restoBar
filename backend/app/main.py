import json
import os
import time
import uuid
from uuid import UUID
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, g, request, send_from_directory
from flask_cors import CORS
from telebot.types import LabeledPrice

load_dotenv()

from . import auth, bot
from .config import Settings
from .extensions import build_queue, build_redis_client, db
from .observability.logging import configure_logging
from .observability.metrics import ORDER_CREATE_ERRORS, ORDERS_CREATED, REQUEST_COUNT, REQUEST_LATENCY, WEBHOOK_DUPLICATES, metrics_payload
from .observability.sentry import init_sentry
from .services.idempotency_service import register_telegram_update
from .services.admin_auth_service import issue_admin_session, resolve_active_membership, upsert_user_from_telegram
from .services.admin_auth_service import read_admin_session
from .services.admin_menu_service import (
    create_menu_category,
    create_menu_item,
    list_menu_categories,
    list_menu_items,
    soft_delete_menu_item,
    toggle_item_availability,
    update_menu_category,
    update_menu_item,
)
from .services.admin_restaurant_service import create_restaurant, delete_restaurant, list_restaurants
from .services.admin_staff_service import StaffPermissionError, change_staff_role, invite_staff_member, list_staff, revoke_staff_member
from .services.client_experience_service import (
    get_cafe_info_payload,
    get_client_theme_public,
    get_client_theme_for_restaurant,
    set_cafe_info_payload,
    set_client_theme,
)
from .services.menu_service import (
    get_cafe_info_from_pg,
    get_categories_from_pg,
    get_category_menu_from_pg,
    get_menu_item_details_from_pg,
    get_popular_menu_from_pg,
)
from .services.storage_service import generate_idempotency_key, mirror_order_to_json, persist_order

def create_app() -> Flask:
    configure_logging()
    init_sentry()
    settings = Settings.from_env()
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SETTINGS"] = settings

    db.init_app(app)
    app.redis_client = build_redis_client(settings.redis_url)
    app.task_queue = build_queue(app.redis_client, settings.rq_queue_name)
    bot.configure_runtime(queue=app.task_queue, settings=settings, app=app)

    allowed_origins = [settings.app_url, settings.admin_app_url]
    if settings.dev_mode:
        allowed_origins.append(settings.dev_app_url)
        allowed_origins.append(settings.admin_dev_app_url)
        bot.enable_debug_logging()
    CORS(app, origins=[origin for origin in allowed_origins if origin is not None])

    @app.before_request
    def before_request():
        g.correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        g.started_at = time.time()

    @app.after_request
    def after_request(response):
        duration = time.time() - getattr(g, "started_at", time.time())
        endpoint = request.endpoint or "unknown"
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)
        response.headers["X-Correlation-ID"] = g.correlation_id
        return response

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    frontend_root = Path(__file__).resolve().parents[2] / "client-web" / "dist"
    legacy_frontend_root = Path(__file__).resolve().parents[2] / "frontend"
    admin_frontend_root = Path(__file__).resolve().parents[2] / "admin-web" / "dist"
    settings = app.config["SETTINGS"]
    admin_host = urlparse(settings.admin_app_url).hostname if settings.admin_app_url else None

    def is_admin_host_request() -> bool:
        request_host = request.host.split(":", 1)[0].lower()
        return admin_host is not None and request_host == admin_host.lower()

    def get_admin_principal():
        settings = app.config["SETTINGS"]
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return None
        return read_admin_session(settings.admin_session_secret, token)

    @app.route("/metrics")
    def metrics():
        return metrics_payload(), 200, {"Content-Type": "text/plain; version=0.0.4"}

    @app.route(bot.WEBHOOK_PATH, methods=["POST"])
    def bot_webhook():
        payload = request.get_json() or {}
        update_id = payload.get("update_id")
        if update_id is not None:
            is_new = register_telegram_update(update_id=update_id, payload=payload)
            if not is_new:
                WEBHOOK_DUPLICATES.inc()
                return {"message": "Duplicate update ignored"}

        bot.process_update(payload)
        return {"message": "OK"}

    @app.route("/info")
    def info():
        settings = app.config["SETTINGS"]
        if settings.read_menu_from_pg:
            info_payload = get_cafe_info_from_pg()
            if info_payload is not None or not settings.json_menu_fallback:
                if info_payload is None:
                    return {"message": "Could not find info data."}, 404
                return info_payload
        try:
            return json_data("data/info.json")
        except FileNotFoundError:
            return {"message": "Could not find info data."}, 404

    @app.route("/categories")
    def categories():
        settings = app.config["SETTINGS"]
        if settings.read_menu_from_pg:
            categories_data = get_categories_from_pg()
            if categories_data or not settings.json_menu_fallback:
                return categories_data
        try:
            return json_data("data/categories.json")
        except FileNotFoundError:
            return {"message": "Could not find categories data."}, 404

    @app.route("/menu/popular")
    def popular_menu():
        raw_limit = request.args.get("limit", "10")
        try:
            parsed_limit = int(raw_limit)
        except (TypeError, ValueError):
            return {"message": "limit must be an integer."}, 400
        if parsed_limit < 1:
            return {"message": "limit must be greater than 0."}, 400

        return get_popular_menu_from_pg(limit=parsed_limit)

    @app.route("/client/theme")
    def client_theme_public():
        restaurant_id = request.args.get("restaurantId")
        try:
            return get_client_theme_public(restaurant_id)
        except ValueError:
            return {"message": "restaurantId must be a valid UUID."}, 400

    @app.route("/client/bootstrap")
    def client_bootstrap():
        raw_limit = request.args.get("popularLimit", "10")
        try:
            parsed_limit = int(raw_limit)
        except (TypeError, ValueError):
            return {"message": "popularLimit must be an integer."}, 400
        if parsed_limit < 1:
            return {"message": "popularLimit must be greater than 0."}, 400

        settings = app.config["SETTINGS"]
        info_payload = None
        categories_payload = []
        if settings.read_menu_from_pg:
            info_payload = get_cafe_info_from_pg()
            categories_payload = get_categories_from_pg()
        if info_payload is None:
            try:
                info_payload = json_data("data/info.json")
            except FileNotFoundError:
                info_payload = None
        if not categories_payload:
            try:
                categories_payload = json_data("data/categories.json")
            except FileNotFoundError:
                categories_payload = []

        return {
            "info": info_payload,
            "categories": categories_payload,
            "popular": get_popular_menu_from_pg(limit=parsed_limit),
            "theme": get_client_theme_public(request.args.get("restaurantId")),
        }

    @app.route("/menu/<category_id>")
    def category_menu(category_id: str):
        settings = app.config["SETTINGS"]
        if settings.read_menu_from_pg:
            menu_data = get_category_menu_from_pg(category_id)
            if menu_data or not settings.json_menu_fallback:
                return menu_data
        try:
            return json_data(f"data/menu/{category_id}.json")
        except FileNotFoundError:
            return {"message": f"Could not find `{category_id}` category data."}, 404

    @app.route("/menu/details/<menu_item_id>")
    def menu_item_details(menu_item_id: str):
        settings = app.config["SETTINGS"]
        if settings.read_menu_from_pg:
            menu_item = get_menu_item_details_from_pg(menu_item_id)
            if menu_item is not None or not settings.json_menu_fallback:
                if menu_item is None:
                    return {"message": f"Could not menu item data with `{menu_item_id}` ID."}, 404
                return menu_item
        try:
            data_folder_path = "data/menu"
            for data_file in os.listdir(data_folder_path):
                menu_items = json_data(f"{data_folder_path}/{data_file}")
                desired_menu_item = next((menu_item for menu_item in menu_items if menu_item["id"] == menu_item_id), None)
                if desired_menu_item is not None:
                    return desired_menu_item
            return {"message": f"Could not menu item data with `{menu_item_id}` ID."}, 404
        except FileNotFoundError:
            return {"message": f"Could not menu item data with `{menu_item_id}` ID."}, 404

    @app.route("/order", methods=["POST"])
    def create_order():
        settings = app.config["SETTINGS"]
        request_data = request.get_json() or {}

        auth_data = request_data.get("_auth")
        if auth_data is None or not auth.validate_auth_data(bot.BOT_TOKEN, auth_data):
            return {"message": "Request data should contain auth data."}, 401

        parsed_auth_data = auth.parse_auth_data(auth_data)
        if parsed_auth_data is None or "user" not in parsed_auth_data:
            return {"message": "Request data should contain parsable auth user data."}, 401

        order_items = request_data.get("cartItems")
        if order_items is None:
            ORDER_CREATE_ERRORS.inc()
            return {"message": "Cart Items are not provided."}, 400

        labeled_prices = []
        for order_item in order_items:
            name = order_item["cafeItem"]["name"]
            variant = order_item["variant"]["name"]
            cost = order_item["variant"]["cost"]
            quantity = order_item["quantity"]
            price = int(cost) * int(quantity)
            labeled_price = LabeledPrice(label=f"{name} ({variant}) x{quantity}", amount=price)
            labeled_prices.append(labeled_price)

        order_id = None
        if settings.dual_write_orders:
            idempotency_key = generate_idempotency_key(request.headers.get("Idempotency-Key"))
            order_id = persist_order(order_items=order_items, telegram_user=parsed_auth_data["user"], idempotency_key=idempotency_key)
            ORDERS_CREATED.inc()
            if settings.write_orders_to_json:
                mirror_order_to_json(
                    order_id=order_id,
                    telegram_user=parsed_auth_data["user"],
                    order_items=order_items,
                    target_file=Path(settings.orders_json_path),
                )

        invoice_payload = order_id if order_id is not None else "orderID"
        invoice_url = bot.create_invoice_link(prices=labeled_prices, payload=invoice_payload)
        return {"invoiceUrl": invoice_url, "orderId": order_id}

    @app.route("/admin/auth/telegram", methods=["POST"])
    def admin_auth_telegram():
        settings = app.config["SETTINGS"]
        request_data = request.get_json() or {}
        if not auth.validate_telegram_login_payload(settings.bot_token or "", request_data):
            return {"message": "Invalid Telegram login payload."}, 401

        telegram_user_id = request_data.get("id")
        if telegram_user_id is None:
            return {"message": "Telegram user id is required."}, 400

        principal = resolve_active_membership(int(telegram_user_id), request_data.get("username"))
        if principal is None:
            return {"message": "Access denied. Pre-approved access required."}, 403

        user = upsert_user_from_telegram(
            telegram_user_id=int(telegram_user_id),
            first_name=request_data.get("first_name"),
            last_name=request_data.get("last_name"),
            username=request_data.get("username"),
        )
        db.session.add(user)
        db.session.commit()

        access_token = issue_admin_session(settings.admin_session_secret, principal)
        return {
            "accessToken": access_token,
            "principal": {
                "telegramUserId": principal.telegram_user_id,
                "restaurantId": principal.restaurant_id,
                "role": principal.role,
                "username": principal.username,
            },
        }

    @app.route("/admin/auth/webapp", methods=["POST"])
    def admin_auth_webapp():
        settings = app.config["SETTINGS"]
        request_data = request.get_json() or {}
        init_data = request_data.get("initData")
        if not isinstance(init_data, str) or not init_data.strip():
            return {"message": "initData is required."}, 400

        if not auth.validate_auth_data(settings.bot_token or "", init_data):
            return {"message": "Invalid Telegram WebApp payload."}, 401

        parsed = auth.parse_auth_data(init_data)
        if parsed is None or "user" not in parsed:
            return {"message": "Could not parse Telegram user payload."}, 401

        user_payload = parsed["user"]
        telegram_user_id = user_payload.get("id")
        if telegram_user_id is None:
            return {"message": "Telegram user id is required."}, 400

        principal = resolve_active_membership(int(telegram_user_id), user_payload.get("username"))
        if principal is None:
            return {"message": "Access denied. Pre-approved access required."}, 403

        user = upsert_user_from_telegram(
            telegram_user_id=int(telegram_user_id),
            first_name=user_payload.get("first_name"),
            last_name=user_payload.get("last_name"),
            username=user_payload.get("username"),
        )
        db.session.add(user)
        db.session.commit()

        access_token = issue_admin_session(settings.admin_session_secret, principal)
        return {
            "accessToken": access_token,
            "principal": {
                "telegramUserId": principal.telegram_user_id,
                "restaurantId": principal.restaurant_id,
                "role": principal.role,
                "username": principal.username,
            },
        }

    @app.route("/admin/staff", methods=["GET"])
    def admin_staff_list():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401

        restaurant_id = request.args.get("restaurantId") or principal.restaurant_id
        include_revoked = request.args.get("includeRevoked") == "1"
        if principal.role != "super_admin" and restaurant_id != principal.restaurant_id:
            return {"message": "Forbidden restaurant scope."}, 403
        return {"items": list_staff(restaurant_id, include_revoked=include_revoked)}

    @app.route("/admin/staff/invite", methods=["POST"])
    def admin_staff_invite():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            membership = invite_staff_member(principal, payload)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code

        return {
            "id": str(membership.id),
            "restaurantId": str(membership.restaurant_id),
            "telegramUserId": membership.telegram_user_id,
            "username": membership.username,
            "phoneNumber": membership.phone_number,
            "role": membership.role.value,
            "status": membership.status.value,
        }, 201

    @app.route("/admin/staff/<membership_id>", methods=["DELETE"])
    def admin_staff_revoke(membership_id: str):
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        try:
            membership = revoke_staff_member(principal, membership_id)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {"id": str(membership.id), "status": membership.status.value}

    @app.route("/admin/staff/<membership_id>/role", methods=["PATCH"])
    def admin_staff_change_role(membership_id: str):
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            membership = change_staff_role(principal, membership_id, payload.get("role", ""))
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {
            "id": str(membership.id),
            "role": membership.role.value,
            "status": membership.status.value,
        }

    @app.route("/admin/restaurants", methods=["GET"])
    def admin_restaurants_list():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        return {"items": list_restaurants(principal)}

    @app.route("/admin/restaurants", methods=["POST"])
    def admin_restaurants_create():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            restaurant = create_restaurant(principal, payload)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {
            "id": str(restaurant.id),
            "name": restaurant.name,
            "slug": restaurant.slug,
            "isActive": restaurant.is_active,
        }, 201

    @app.route("/admin/restaurants/<restaurant_id>", methods=["DELETE"])
    def admin_restaurants_delete(restaurant_id: str):
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        try:
            restaurant = delete_restaurant(principal, restaurant_id)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {
            "id": str(restaurant.id),
            "name": restaurant.name,
            "slug": restaurant.slug,
            "isActive": restaurant.is_active,
        }

    @app.route("/admin/menu/categories", methods=["GET"])
    def admin_menu_categories_list():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        try:
            items = list_menu_categories(principal, request.args.get("restaurantId"))
        except StaffPermissionError as exc:
            return {"message": exc.message}, exc.status_code
        return {"items": items}

    @app.route("/admin/menu/categories", methods=["POST"])
    def admin_menu_categories_create():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            category = create_menu_category(principal, payload)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {
            "id": category.id,
            "name": category.name,
            "icon": category.icon,
            "backgroundColor": category.background_color,
            "isActive": category.is_active,
        }, 201

    @app.route("/admin/menu/categories/<category_id>", methods=["PATCH"])
    def admin_menu_categories_update(category_id: str):
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            category = update_menu_category(principal, category_id, payload)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {
            "id": category.id,
            "name": category.name,
            "icon": category.icon,
            "backgroundColor": category.background_color,
            "isActive": category.is_active,
        }

    @app.route("/admin/menu/items", methods=["GET"])
    def admin_menu_items_list():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        try:
            items = list_menu_items(principal, request.args.get("restaurantId"), request.args.get("categoryId"))
        except StaffPermissionError as exc:
            return {"message": exc.message}, exc.status_code
        return {"items": items}

    @app.route("/admin/menu/items", methods=["POST"])
    def admin_menu_items_create():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            item = create_menu_item(principal, payload)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {
            "id": item.id,
            "name": item.name,
            "categoryId": item.category_id,
            "isAvailableNow": item.is_available_now,
            "isPopular": item.is_popular,
        }, 201

    @app.route("/admin/menu/items/<menu_item_id>", methods=["PATCH"])
    def admin_menu_items_update(menu_item_id: str):
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            item = update_menu_item(principal, menu_item_id, payload)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {
            "id": item.id,
            "name": item.name,
            "categoryId": item.category_id,
            "discountMinor": item.discount_minor,
            "discountIsActive": item.discount_is_active,
            "isAvailableNow": item.is_available_now,
            "isPopular": item.is_popular,
        }

    @app.route("/admin/client/theme", methods=["GET"])
    def admin_client_theme_get():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        return get_client_theme_for_restaurant(UUID(principal.restaurant_id))

    @app.route("/admin/client/theme", methods=["PATCH"])
    def admin_client_theme_patch():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            config = set_client_theme(principal, payload)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return config

    @app.route("/admin/cafe-info", methods=["GET"])
    def admin_cafe_info_get():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = get_cafe_info_payload()
        return payload or {}

    @app.route("/admin/cafe-info", methods=["PATCH"])
    def admin_cafe_info_patch():
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        try:
            result = set_cafe_info_payload(principal, payload)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return result

    @app.route("/admin/menu/items/<menu_item_id>", methods=["DELETE"])
    def admin_menu_items_delete(menu_item_id: str):
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        try:
            item = soft_delete_menu_item(principal, menu_item_id)
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {"id": item.id, "isActive": item.is_active}

    @app.route("/admin/menu/items/<menu_item_id>/availability", methods=["PATCH"])
    def admin_menu_items_toggle_availability(menu_item_id: str):
        principal = get_admin_principal()
        if principal is None:
            return {"message": "Unauthorized."}, 401
        payload = request.get_json() or {}
        if "isAvailableNow" not in payload:
            return {"message": "isAvailableNow is required."}, 400
        try:
            item = toggle_item_availability(principal, menu_item_id, bool(payload["isAvailableNow"]))
            db.session.commit()
        except StaffPermissionError as exc:
            db.session.rollback()
            return {"message": exc.message}, exc.status_code
        return {"id": item.id, "isAvailableNow": item.is_available_now}

    @app.route("/")
    def frontend_index():
        if is_admin_host_request():
            if not admin_frontend_root.exists():
                return {"message": "Admin frontend build is missing. Run: cd admin-web && npm run build"}, 404
            return send_from_directory(admin_frontend_root, "index.html")
        if not frontend_root.exists() and legacy_frontend_root.exists():
            return send_from_directory(legacy_frontend_root, "index.html")
        if not frontend_root.exists():
            return {"message": "Client frontend build is missing. Run: cd client-web && npm run build"}, 404
        return send_from_directory(frontend_root, "index.html")

    @app.route("/admin")
    @app.route("/admin/")
    def admin_frontend_index():
        if not admin_frontend_root.exists():
            return {"message": "Admin frontend build is missing. Run: cd admin-web && npm run build"}, 404
        return send_from_directory(admin_frontend_root, "index.html")

    @app.route("/admin/<path:asset_path>")
    def admin_frontend_assets(asset_path: str):
        if not admin_frontend_root.exists():
            return {"message": "Admin frontend build is missing. Run: cd admin-web && npm run build"}, 404
        asset_file = admin_frontend_root / asset_path
        if asset_file.is_file():
            return send_from_directory(admin_frontend_root, asset_path)
        return send_from_directory(admin_frontend_root, "index.html")

    @app.route("/<path:asset_path>")
    def frontend_assets(asset_path: str):
        if is_admin_host_request():
            admin_asset_file = admin_frontend_root / asset_path
            if admin_asset_file.is_file():
                return send_from_directory(admin_frontend_root, asset_path)
            return send_from_directory(admin_frontend_root, "index.html")

        if not frontend_root.exists() and legacy_frontend_root.exists():
            asset_file = legacy_frontend_root / asset_path
            if asset_file.is_file():
                return send_from_directory(legacy_frontend_root, asset_path)
            return {"message": "Not found"}, 404

        asset_file = frontend_root / asset_path
        if asset_file.is_file():
            return send_from_directory(frontend_root, asset_path)
        if frontend_root.exists():
            return send_from_directory(frontend_root, "index.html")
        return {"message": "Not found"}, 404


def json_data(data_file_path: str):
    if os.path.exists(data_file_path):
        with open(data_file_path, "r", encoding="utf-8") as data_file:
            return json.load(data_file)
    raise FileNotFoundError()


app = create_app()
settings = app.config["SETTINGS"]
if settings.bot_mode == "webhook" and bot.BOT_TOKEN and bot.WEBHOOK_URL and os.getenv("SKIP_WEBHOOK_REFRESH") != "1":
    bot.refresh_webhook()
