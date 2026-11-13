# GymOS (Owner-side)

Owner-side Gym Operating System for gyms in India: tools for owner and staff only, plus an AI WhatsApp chatbot for people who message the gym. No member-facing app and no member login.

## Scope
- **IN:** Owner/staff panels and workflows, plus the AI WhatsApp chatbot (grounded FAQ, trial booking/lead capture into CRM, human handoff with guardrails).
- **OUT:** No QR/NFC/member attendance, no member app/PWA/login, no AI Gym Manager, no automated lead follow-up sequences, no workout/diet AI, no progress tracking/inactive/retention/renewal AI, no occupancy analytics/forecasting/AI business recs, no face check-in/predictive maintenance.

## Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL, Redis, Celery (jobs/schedulers)
- **Frontend:** React + Vite + TypeScript + Tailwind (Owner, Admin, Reception, Trainer panels)
- **Auth:** JWT + RBAC (owner, admin, reception, trainer)
- **Messaging:** WhatsApp Business Cloud API behind provider interface (mock in dev/tests)
- **Payments:** Razorpay/UPI behind provider interface (mock in dev/tests)
- **AI:** Provider-agnostic LLM interface used only by the WhatsApp chatbot; falls back to canned replies + human handoff if unavailable
- **Tests/CI:** pytest + Playwright, GitHub Actions

## Repository layout
- `backend/` — FastAPI service, domain logic, migrations, workers
- `frontend/` — React + Vite web app (staff panels)
- `infra/` — Docker and infra configuration
- `docs/` — documentation and ADRs (`docs/adr/`)
- `PLAN.md`, `BACKLOG.md`, `PROGRESS.md`, `DECISIONS.md`, `BLOCKERS.md` — project state

## Getting started (local development)

### Prerequisites
- Docker Desktop (with Docker Compose)
- Python 3.12+ (for running backend/tests outside containers)
- Node.js 20+ (for frontend, added in later phases)

### Setup
1. Copy environment template: `cp .env.example .env` (never commit secrets).
2. Start the stack: `docker compose up --build`
3. Backend (local): `cd backend`, create venv, install deps (`pip install -e ".[dev]"` or as configured), then `uvicorn app.main:app --reload`
4. Run tests: `pytest`

> Real integrations (WhatsApp, Razorpay, LLM) use mocks in dev/tests until credentials exist. See `BLOCKERS.md`.

## Principles
- Multi-tenant from day one: every table carries `gym_id` and `branch_id`; tenant-scoped queries.
- All outbound WhatsApp messages logged (who/what/why, template). Respect consent/opt-out (DPDP Act); only approved templates for business-initiated messages.
- Chatbot answers grounded in gym data only; escalate on medical/health/refunds/complaints or uncertainty; never invent prices/promises.
- No feature without a test.
