import os

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration


def init_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
    )
