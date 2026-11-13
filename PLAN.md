# GymOS — Plan

## Vision
Gym Operating System for gyms in India (not just management software). Multi-tenant (gym + branch), with operations, communication, payments, and AI-assisted workflows that degrade gracefully.

## Stack (fixed unless ADR in /docs/adr/)
- Backend: Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL, Redis, Celery (or ARQ)
- Frontend: React + Vite + TypeScript + Tailwind (admin/reception/trainer/owner panels); member app as PWA first
- Auth: JWT + RBAC (owner, admin, reception, trainer, member)
- Multi-tenant from day one: every table carries `gym_id` and `branch_id`; all queries tenant-scoped
- Messaging: WhatsApp Business Cloud API behind provider interface (mock for dev/tests)
- Payments: Razorpay/UPI behind provider interface (mock for dev/tests)
- AI: provider-agnostic LLM interface; all AI features must degrade gracefully to rule-based logic if LLM unavailable
- Tests: pytest + Playwright; CI via GitHub Actions

## Phases & Milestones

### Phase 0: Foundation
**Goal:** Runnable multi-tenant skeleton with CI, core schema, auth/RBAC, provider interfaces, mocks, and job scheduler/event bus.
- M0.1 Repo structure, Docker Compose (api, db, redis, worker), env/config
- M0.2 CI (lint, type-check, tests), code quality tooling
- M0.3 Multi-tenant core schema (gym, branch, user, role/membership), migrations, audit log
- M0.4 Auth (JWT) and RBAC enforcement
- M0.5 Provider interfaces + mocks: messaging, payments, LLM
- M0.6 Event bus / job scheduler for reminders and automations

### Phase 1: Core Operations (MVP)
**Goal:** End-to-end gym operations for members, attendance, payments, WhatsApp reminders, staff/trainers, leads, and role-based panels/PWA.
- M1.1 Member lifecycle & profiles
- M1.2 Plans, memberships, billing basics (GST-ready receipts/invoices)
- M1.3 Attendance (QR/NFC optional), sharing detection
- M1.4 Payments & dues tracking
- M1.5 WhatsApp templates and automated reminders (via mock in dev)
- M1.6 Trainers, sessions, staff attendance/payroll records
- M1.7 Expenses, dashboards, leads CRM
- M1.8 Reception/Admin/Trainer panels and Member PWA

### Phase 2: AI Automation
**Goal:** AI-assisted operations with approval/audit, grounded responses, transparent scoring, and graceful rule-based fallbacks.
- M2.1 AI Gym Manager daily briefing + suggested actions
- M2.2 AI WhatsApp agent (FAQs, trial booking, lead capture, handoff)
- M2.3 Inactive-member detection and re-engagement
- M2.4 Automated lead follow-up sequences
- M2.5 Workout/diet generation with trainer review & safety flags
- M2.6 Progress tracking and charts
- M2.7 Complaint management with SLA
- M2.8 Renewal prediction & retention alerts (transparent scoring)

### Phase 3: Advanced
**Goal:** Multi-branch intelligence, occupancy analytics, maintenance/forecasting, and optional consent-gated biometrics.
- M3.1 Multi-branch owner dashboard & comparisons
- M3.2 Live occupancy & peak-hour analytics
- M3.3 Equipment registry & maintenance
- M3.4 Demand/revenue forecasting
- M3.5 AI business recommendations
- M3.6 Optional face check-in (consent-gated) + hardware integration docs

## Cross-cutting Principles
- Every AI/member-contact action goes through approval/audit layer (auto-send or staff-approve) with logs of who/what/why.
- Consent and opt-out for WhatsApp and biometric data (DPDP Act). Face check-in opt-in only; store embeddings, not photos.
- Real integrations (WhatsApp, Razorpay, face recognition, NFC hardware) use mocks and are marked "needs credentials/hardware" in BLOCKERS.md. Never fake real operation.
- No secrets in code; `.env` + `.env.example`.
- One task per iteration, tests first, real results logged.
- Prefer boring, working code over clever code. No feature without a test.
