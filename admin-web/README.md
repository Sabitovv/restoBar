# Admin Web (React + Vite)

Admin panel shell with Telegram WebApp-only auth for pre-approved staff.

## Local run

1. Copy env:

```bash
cp .env.example .env
```

2. Install and run:

```bash
npm install
npm run dev
```

## Required env vars

- `VITE_API_BASE_URL` - backend URL, example `http://localhost:5000`

## Auth mode

- Admin panel is WebApp-only.
- Open it from Telegram bot via `Open Admin` button.
- Browser-only open (without Telegram WebApp `initData`) shows guidance screen and does not authenticate.
