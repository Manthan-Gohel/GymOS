# GymOS

Gym Operating System for gyms in India (operations, members, attendance, payments, messaging, and AI-assisted workflows). Multi-tenant (gym + branch) by design.

## Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL, Redis, Celery (jobs/schedulers)
- **Frontend:** React + Vite + TypeScript + Tailwind (admin/reception/trainer/owner panels); member app as PWA
- **Auth:** JWT + RBAC (owner, admin, reception, trainer, member)
- **Messaging:** WhatsApp Business Cloud API behind provider interface (mock in dev/tests)
- **Payments:** Razorpay/UPI behind provider interface (mock in dev/tests)
- **AI:** Provider-agnostic LLM interface with graceful rule-based fallback
- **Tests/CI:** pytest + Playwright, GitHub Actions

## Repository layout
- `backend/` — FastAPI service, domain logic, migrations, workers
- `frontend/` — React + Vite web app (panels and member PWA)
- `infra/` — Docker and infra configuration
- `docs/` — documentation and ADRs (`docs/adr/`)
- `PLAN.md`, `BACKLOG.md`, `PROGRESS.md`, `DECISIONS.md`, `BLOCKERS.md` — project state

## Getting started (local development)

### Prerequisites
- Docker Desktop (with Docker Compose)
- Python 3.12+ (for running backend/tests outside containers)
- Node.js 20+ (for frontend, added in later phases)

### Setup
1. Copy environment template:
   ```bash
   cp .env.example .env
   ```
   (Adjust values as needed; never commit secrets.)

2. Start the stack:
   ```bash
   docker compose up --build
   ```
   Services (as they are added): `api`, `db` (PostgreSQL), `redis`, `worker`.

3. Run backend locally (alternative/dev workflow, once bootstrapped in `backend/`):
   ```bash
   cd backend
   python -m venv .venv
   # activate venv, then install deps
   pip install -e .  # or project-defined install command
   uvicorn app.main:app --reload
   ```

4. Run tests:
   ```bash
   pytest
   ```

> Note: This repo is being built iteratively. See `PROGRESS.md` for current status, `BLOCKERS.md` for items needing credentials/hardware, and `BACKLOG.md` for planned work. Real integrations (WhatsApp, Razorpay, biometrics/NFC hardware) use mocks in dev/tests.

## Principles
- Multi-tenant from day one: every table carries `gym_id` and `branch_id`; tenant-scoped queries.
- AI/member-contact actions go through approval/audit (auto-send or staff-approve) with logs.
- Consent and opt-out respected (WhatsApp, biometrics opt-in only; embeddings not photos).
- No feature without a test.
