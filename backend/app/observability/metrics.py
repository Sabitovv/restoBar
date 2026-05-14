from prometheus_client import Counter, Histogram, generate_latest


REQUEST_COUNT = Counter("http_requests_total", "HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_latency_seconds", "HTTP request latency", ["method", "endpoint"])
ORDERS_CREATED = Counter("orders_created_total", "Total created orders")
ORDER_CREATE_ERRORS = Counter("order_create_errors_total", "Total order creation errors")
WEBHOOK_DUPLICATES = Counter("webhook_duplicate_updates_total", "Duplicate Telegram updates")
PAYMENTS_MARKED_PAID = Counter("payments_marked_paid_total", "Successful paid transitions")
PAYMENTS_MARK_FAILED = Counter("payments_mark_failed_total", "Failed paid transitions")


def metrics_payload() -> bytes:
    return generate_latest()
