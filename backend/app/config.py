import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_url: str | None
    admin_app_url: str | None
    dev_mode: bool
    dev_app_url: str | None
    admin_dev_app_url: str | None
    webhook_url: str | None
    bot_token: str | None
    payment_provider_token: str | None
    database_url: str
    redis_url: str
    ai_request_timeout_seconds: int
    ai_max_retries: int
    ai_model: str
    ai_web_search_enabled: bool
    tavily_api_key: str | None
    tavily_timeout_seconds: int
    tavily_max_results: int
    dual_write_orders: bool
    write_orders_to_json: bool
    orders_json_path: str
    enable_ai_bot_replies: bool
    rq_queue_name: str
    read_menu_from_pg: bool
    json_menu_fallback: bool
    bot_mode: str
    admin_session_secret: str

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            app_url=os.getenv("APP_URL"),
            admin_app_url=os.getenv("ADMIN_APP_URL"),
            dev_mode=os.getenv("DEV_MODE") is not None,
            dev_app_url=os.getenv("DEV_APP_URL"),
            admin_dev_app_url=os.getenv("ADMIN_DEV_APP_URL"),
            webhook_url=os.getenv("WEBHOOK_URL"),
            bot_token=os.getenv("BOT_TOKEN"),
            payment_provider_token=os.getenv("PAYMENT_PROVIDER_TOKEN"),
            database_url=os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/tma_cafe"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            ai_request_timeout_seconds=int(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "10")),
            ai_max_retries=int(os.getenv("AI_MAX_RETRIES", "2")),
            ai_model=os.getenv("AI_MODEL", "gemini-2.5-flash"),
            ai_web_search_enabled=os.getenv("AI_WEB_SEARCH_ENABLED", "1") == "1",
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            tavily_timeout_seconds=int(os.getenv("TAVILY_TIMEOUT_SECONDS", "7")),
            tavily_max_results=int(os.getenv("TAVILY_MAX_RESULTS", "3")),
            dual_write_orders=os.getenv("DUAL_WRITE_ORDERS", "1") == "1",
            write_orders_to_json=os.getenv("WRITE_ORDERS_TO_JSON", "1") == "1",
            orders_json_path=os.getenv("ORDERS_JSON_PATH", "data/orders.json"),
            enable_ai_bot_replies=os.getenv("ENABLE_AI_BOT_REPLIES", "1") == "1",
            rq_queue_name=os.getenv("RQ_QUEUE_NAME", "ai"),
            read_menu_from_pg=os.getenv("READ_MENU_FROM_PG", "1") == "1",
            json_menu_fallback=os.getenv("JSON_MENU_FALLBACK", "1") == "1",
            bot_mode=os.getenv("BOT_MODE", "webhook").strip().lower(),
            admin_session_secret=os.getenv("ADMIN_SESSION_SECRET", os.getenv("BOT_TOKEN", "dev-admin-secret")),
        )
