# AGENTS

## Repo shape (what matters)
- Two runnable apps share one backend: `backend` (Flask API + Telegram bot + admin APIs) and `admin-web` (React/Vite admin UI).
- Customer Mini App frontend is static files under `frontend/` (no package manager/scripts there); Flask serves these files directly.
- Main backend entrypoint is `backend/app/main.py` (`app = create_app()`), and webhook refresh runs at import time unless `SKIP_WEBHOOK_REFRESH=1`.

## Verified local run commands
- Infra first: `docker compose up -d postgres redis` (from repo root).
- Backend setup/run (from `backend/`): `pip install -r requirements.txt`, then `alembic upgrade head`, then `flask --app app.main:app run`.
- Polling mode for local bot work: copy `backend/.env.polling` to `backend/.env`, then run `python -m app.run_bot_polling`.
- Webhook mode template: `backend/.env.webhook`.
- Admin UI (from `admin-web/`): `npm install`, `npm run dev`.

## Test and validation shortcuts
- Backend tests run with `pytest` from `backend/`.
- Run a single backend test file: `pytest tests/test_admin_auth_service.py`.
- Admin UI checks: `npm run lint`, `npm run build` (from `admin-web/`).

## Data/migration workflow quirks
- Menu and cafe data migration is JSON -> Postgres via `backend/scripts/seed_json_to_pg.py`; run after `alembic upgrade head`.
- Migration toggles are env-driven in `backend/app/config.py` (`READ_MENU_FROM_PG`, `JSON_MENU_FALLBACK`, `DUAL_WRITE_ORDERS`, `WRITE_ORDERS_TO_JSON`). Defaults are enabled (`"1"`), so behavior is PG-first with JSON fallback and dual-write on.
- Alembic reads `DATABASE_URL` if set (`backend/migrations/env.py`), otherwise uses `backend/alembic.ini` local default.

## Serving/admin-host behavior to avoid confusion
- Backend serves `admin-web/dist` for `/admin` routes and for `/` when request host matches `ADMIN_APP_URL` host.
- If `admin-web/dist` is missing, backend returns a 404 with explicit instruction to run `cd admin-web && npm run build`.

## Config/doc mismatches to trust code over prose
- Root README mentions `backend/.env.example`, but repository currently uses `backend/.env.polling` and `backend/.env.webhook` templates.
