# Telegram Cafe Production Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the existing Telegram Mini App backend from JSON storage to a production-ready architecture with PostgreSQL, Redis, async AI worker, and safe phased rollout.

**Architecture:** Keep Flask API and webhook as synchronous entrypoints, move durable state into PostgreSQL, move coordination and anti-abuse into Redis, and process AI work asynchronously via a worker queue. Roll out by feature flags with dual-write and consistency checks before cutover.

**Tech Stack:** Flask, SQLAlchemy, Alembic, psycopg, Redis, RQ, python-telegram-bot API client, Sentry, Prometheus client.

---

### Task 1: Foundation and configuration

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/extensions.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

- [ ] Add typed environment-driven settings for DB, Redis, queue, AI, and security.
- [ ] Extract app initialization into reusable app factory structure while preserving existing endpoints.
- [ ] Register extension placeholders (db, redis, queue, observability) without breaking current behavior.

### Task 2: PostgreSQL domain schema and persistence baseline

**Files:**
- Create: `backend/app/models/*.py`
- Create: `backend/app/repositories/*.py`
- Create: `backend/migrations/*`

- [ ] Implement tables: users, menu categories/items/variants, orders/items, payments, conversations/messages/events, processed updates.
- [ ] Add indexes and constraints for idempotency and transactional safety.
- [ ] Add initial Alembic migration for schema bootstrap.

### Task 3: Redis state and idempotency

**Files:**
- Create: `backend/app/services/idempotency_service.py`
- Create: `backend/app/services/lock_service.py`

- [ ] Implement update deduplication by Telegram update_id.
- [ ] Implement short-lived user lock for message/payment race prevention.
- [ ] Add API-level idempotency helper for order/payment creation.

### Task 4: Worker and AI processing skeleton

**Files:**
- Create: `backend/app/workers/ai_tasks.py`
- Create: `backend/app/services/ai_service.py`
- Create: `backend/app/services/prompt_builder.py`

- [ ] Add async task enqueue from webhook path.
- [ ] Persist incoming/outgoing bot messages in PostgreSQL.
- [ ] Add guarded LLM call skeleton with timeout, retries, fallback, and telemetry fields.

### Task 5: Dual-write migration and seed

**Files:**
- Create: `backend/scripts/seed_json_to_pg.py`
- Create: `backend/scripts/consistency_checks.py`
- Modify: `backend/app/main.py`

- [ ] Seed menu data from JSON to PostgreSQL.
- [ ] Introduce feature flags to dual-write orders/payments/messages.
- [ ] Add consistency checker comparing JSON and PostgreSQL transactional records.

### Task 6: Security and observability hardening

**Files:**
- Modify: `backend/app/auth.py`
- Create: `backend/app/observability/*.py`

- [ ] Tighten Telegram auth verification and expiration checks.
- [ ] Add structured logs with correlation_id, user_id, order_id, update_id.
- [ ] Add Sentry and Prometheus initialization hooks.

### Task 7: Validation and rollout gates

**Files:**
- Create: `backend/tests/*`
- Modify: `README.md`

- [ ] Add smoke tests for create order, payment status transition, update dedup.
- [ ] Document staged rollout and rollback playbook.
- [ ] Define cutover criteria and disable JSON read/write plan.
