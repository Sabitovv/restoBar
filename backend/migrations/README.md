# Alembic migrations

Run from `backend` directory.

Set DB URL if needed:

```bash
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/tma_cafe"
```

Upgrade to latest schema:

```bash
alembic upgrade head
```

Create new migration:

```bash
alembic revision --autogenerate -m "describe change"
```
