# GymOS — Plan (Owner-side)

## Vision
Owner-side Gym Operating System for gyms in India, used by owner and staff only. No member-facing app and no member login. The only AI feature is a WhatsApp chatbot for people who message the gym.

## Scope (hard boundaries)
**IN:** owner/staff tools plus the AI WhatsApp chatbot.
**OUT (do not build):** QR/NFC attendance, member attendance of any kind, shared-membership detection, member app/PWA, member role/login, AI Gym Manager, automated lead follow-up sequences, workout/diet AI, progress tracking, inactive-member/retention/renewal AI, occupancy analytics, forecasting, AI business recommendations, face check-in, predictive maintenance.

## Stack (fixed unless ADR in /docs/adr/)
- Backend: Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL, Redis, Celery (or ARQ)
- Frontend: React + Vite + TypeScript + Tailwind (Owner, Admin, Reception, Trainer panels)
- Auth: JWT + RBAC (roles: owner, admin, reception, trainer)
- Multi-tenant from day one: every table has `gym_id` and `branch_id`; all queries tenant-scoped
- Messaging: **openWA** (wa-automate, https://github.com/open-wa/wa-automate-nodejs) behind a provider interface (mock for dev/tests); real use requires openWA session/service setup
- Payments: **YouPI-PG** (https://github.com/youpi-pg/YouPI-PG) behind a provider interface (mock for dev/tests) + staff-entered cash/card recording; real gateway use requires deployment/setup
- AI: provider-agnostic LLM interface, used ONLY by the WhatsApp chatbot; falls back to canned replies + human handoff if the LLM is down (unchanged)
- Tests: pytest + Playwright; CI via GitHub Actions
- Integration ADRs: `docs/adr/0001-messaging-integration-openwa.md`, `docs/adr/0002-payments-integration-youpi-pg.md`

## Phases & Milestones

### Phase 0: Foundation
**Goal:** Runnable multi-tenant skeleton with CI, core schema, auth/RBAC, provider interfaces, mocks, and job scheduler.
- M0.1 Repo, Docker Compose (api, db, redis, worker), env/config
- M0.2 CI, lint/type-check baseline
- M0.3 Multi-tenant schema (gym, branch, user, role), migrations, audit log
- M0.4 Auth (JWT) and RBAC (owner/admin/reception/trainer)
- M0.5 Provider interfaces + mocks: messaging, payments, LLM (chatbot-only usage later)
- M0.6 Job scheduler for reminders

### Phase 1: Owner/staff operations (MVP)
**Goal:** Complete owner/staff operational workflows without member-facing surfaces or attendance features.
- M1.1 Member records (entered by reception): profile, photo, KYC, emergency contact, health notes
- M1.2 Membership plans: purchase, freeze, upgrade, expiry engine
- M1.3 Payments: cash/UPI/card, dues, partial payments, late fees, receipts/GST-ready invoices
- M1.4 WhatsApp templated reminders (non-AI): welcome, expiry (7/3/1), payment due, template management, opt-out
- M1.5 Trainer management: profiles, availability, member assignment, session booking, trainer attendance
- M1.6 Staff attendance (manual check-in by admin) + payroll records
- M1.7 Expenses + daily revenue/expense/profit dashboard
- M1.8 Leads/enquiries CRM (manual): capture, status, trial booking, notes
- M1.9 Complaint log (manual): status, assignee, resolution
- M1.10 Equipment registry + manual maintenance schedules and reminders
- M1.11 Panels: Owner dashboard, Admin, Reception, Trainer

### Phase 2: AI WhatsApp chatbot (only AI feature)
**Goal:** Grounded inbound WhatsApp chatbot with lead capture, handoff, and strict guardrails.
- M2.1 Inbound webhook + conversation store
- M2.2 Grounded FAQ answers: timings, fees, plans, trainers, location
- M2.3 Trial booking and lead capture into leads CRM
- M2.4 Human handoff + staff inbox, bot paused while staff reply
- M2.5 Guardrails: no hallucinated prices, escalation keywords, per-number rate limits, full conversation audit log
- M2.6 Eval set of sample questions with expected grounded answers

### Phase 3: Multi-branch
**Goal:** Owner visibility and controls across branches.
- M3.1 Owner dashboard across branches with revenue/expense comparison
- M3.2 Branch-level permissions

## Cross-cutting Principles
- All outbound WhatsApp messages (reminders and chatbot replies) are logged (who/what/why, template used). Respect consent and opt-out (DPDP Act) and policy-compliant business messaging; use approved/controlled templates where applicable (note: openWA is WhatsApp Web-based, not Cloud API templates; see ADR 0001).
- Chatbot answers must be strictly grounded in gym's own data (timings, fees, plans, trainers, offers). If unsure or asked about medical/health/refunds/complaints, hand off to staff. Never invent prices or promises.
- openWA and YouPI-PG integrations use mocks in dev/tests, marked "needs setup/credentials" in BLOCKERS.md. Never fake real operation. LLM/other components remain provider-agnostic with fallback as specified.
- No hardcoded secrets; `.env` + `.env.example`.
- One task per iteration, tests first, real results logged.
- Prefer boring, working code. No feature without a test.
