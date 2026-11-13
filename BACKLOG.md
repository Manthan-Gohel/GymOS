# GymOS — Backlog (owner-side scope)

Format: `- [ ] ID | title | acceptance criteria | deps`
Status legend: `[ ]` todo, `[x]` done, `[~]` blocked

> Scope: owner/staff tools + AI WhatsApp chatbot only. No member app/login, no QR/NFC/member attendance, no non-chatbot AI features (see PLAN.md OUT list).

## Phase 0: Foundation

- [x] P0-01 | Repo scaffold and base directories | `backend/`, `frontend/`, `infra/`, `docs/`, `.gitignore`, and top-level README exist; README describes stack and how to run locally | none
- [x] P0-02 | Backend project bootstrap (FastAPI + Python 3.12) | `backend/pyproject.toml` (or requirements) with FastAPI, SQLAlchemy 2, Alembic, Pydantic, pytest, lint/type tools; `backend/app/main.py` exposes `/health`; `pytest` runs at least one passing health test | P0-01
- [x] P0-03 | Docker Compose dev environment | `docker-compose.yml` defines api, db (Postgres), redis, worker services; `.env.example` provided; `docker compose config`/basic up instructions documented; local dev can start services (documented) | P0-02
- [x] P0-04 | CI pipeline (GitHub Actions) | Workflow runs backend lint, type-check, and tests on push/PR; fails on errors; status documented in README | P0-02
- [x] P0-05 | Linting and type-checking baseline | Ruff and mypy (or pyright) configured for backend with passing baseline; documented commands to run lint/type/test | P0-02
- [x] P0-06 | Multi-tenant core schema and migrations | Alembic initialized; models/tables for gym, branch, user, role (or user_role) all include `gym_id` and `branch_id` where applicable; migration applies cleanly to fresh DB; tests verify tenant columns present | P0-02
- [x] P0-07 | Tenant scoping primitives | Base repository/service/query helpers enforce tenant scoping (gym_id/branch_id) and prevent cross-tenant access; tests prove queries cannot read/write other tenant data | P0-06
- [x] P0-08 | Auth (JWT) and password handling | Login endpoint issues JWT with user/tenant/role claims (roles: owner, admin, reception, trainer); password hashing; auth dependency extracts current user; tests cover success/failure/expiry basics | P0-06
- [x] P0-09 | RBAC enforcement | Role-based access control for owner, admin, reception, trainer; dependency enforces permissions on protected endpoints; tests verify allowed/denied per role | P0-08
- [x] P0-10 | Audit log foundation | Audit log table records actor, tenant, action, entity, timestamp, metadata/why; helper/service to write audit entries; tests verify audit records created for a sample privileged action | P0-07, P0-08
- [x] P0-11 | Provider interface: messaging + mock | Messaging provider interface (send template/message) with mock implementation storing sent messages for tests; config selects mock by default; supports audit-friendly payload (who/what/why/template) | P0-02
- [x] P0-12 | Provider interface: payments + mock | Payments provider interface (record/create/mock payment flow) with mock implementation; config selects mock by default; tests cover basic payment record flow | P0-02
- [x] P0-13 | Provider interface: LLM + mock and canned fallback | LLM provider interface used ONLY for WhatsApp chatbot; mock implementation and explicit canned-replies + human-handoff fallback when LLM unavailable; tests show graceful fallback | P0-02
- [x] P0-14 | Job scheduler for reminders | Celery (or ARQ) worker configured with Redis; task registration and sample scheduled reminder task runs in dev/test mode; tests for task execution path | P0-03
- [x] P0-15 | Foundation integration pass and docs | End-to-end smoke: migrations, auth, tenant scoping + RBAC enforced, provider mocks wired; README/docs updated; all P0 tests green | P0-04, P0-05, P0-07, P0-09, P0-10, P0-11, P0-12, P0-13, P0-14

## Phase 1: Owner/staff operations (MVP)

### 1.1 Member records (staff-entered)
- [x] P1-01 | Member record model and CRUD | Member entity (gym_id, branch_id, profile photo ref, KYC fields, emergency contact, health notes, consent/opt-out flags) entered by reception/admin; create/read/update; validation; tests for tenant scoping | P0-15
- [x] P1-02 | Member record audit and data handling | Member create/update writes audit log entries; sensitive fields handled appropriately; tests verify audit trail | P1-01, P0-10

### 1.2 Plans & memberships
- [x] P1-03 | Membership plans CRUD | Plan entity (name, duration, price, terms metadata) scoped to gym/branch; CRUD endpoints with RBAC; tests | P0-15
- [x] P1-04 | Membership purchase, freeze, upgrade, expiry engine | Membership lifecycle (active/frozen/expired/upgraded/cancelled as needed), purchase flow, freeze/unfreeze, upgrade rules, expiry calculation; scheduled or on-demand expiry processing; tests for transitions and expiry | P1-03, P0-14
- [x] P1-05 | Receipts and GST-ready invoices | Invoice/receipt records with GST-relevant fields (configurable), linked to payments/memberships; generation logic; tests for totals/tax fields | P1-04, P0-12

### 1.3 Payments
- [x] P1-06 | Payment recording and dues | Record cash/UPI/card payments via mock/manual modes, partial payments, dues calculation, late fee rules; tests for balances and edge cases | P1-05
- [x] P1-07 | Payment receipts lookup and status | Issue/lookup receipts, payment status tracking; tests | P1-06

### 1.4 WhatsApp templated reminders (non-AI)
- [x] P1-08 | WhatsApp template/message management and opt-out | Template/message storage and management for business-initiated reminders (controlled/approved content where applicable); member/contact consent and opt-out respected; tests ensure opt-out blocks send; compatible with openWA integration target (ADR 0001) | P1-01, P0-11, P0-10
- [x] P1-09 | Outbound message logging and audit | All outbound WhatsApp messages (reminders and later chatbot replies) logged with who/what/why and template used; queryable audit trail; tests | P1-08
- [x] P1-10 | Automated reminders (welcome, expiry 7/3/1, payment due) | Scheduler/jobs enqueue reminders based on rules; uses messaging mock; respects opt-out and controlled/approved message templates; tests for scheduling and logging | P1-04, P1-06, P1-09, P0-14

### 1.5 Trainers & sessions
- [x] P1-11 | Trainer profiles, availability, member assignment | Trainer entities (staff users/records as appropriate), availability slots, assignment to members; RBAC; tests | P0-15
- [x] P1-12 | Session booking and trainer attendance | Book/cancel/reschedule sessions, track trainer attendance; conflict/availability checks; tests | P1-11

### 1.6 Staff, expenses, dashboard
- [x] P1-13 | Staff attendance (manual by admin) and payroll records | Admin records staff attendance manually; payroll record structures (calculation-ready, not disbursement); tests | P0-15
- [ ] P1-14 | Expenses and daily revenue/expense/profit dashboard API | Expense tracking and aggregated metrics endpoints for daily revenue/expense/profit; tests for calculations | P1-06, P1-13

### 1.7 CRM, complaints, equipment
- [ ] P1-15 | Leads/enquiries CRM (manual) | Lead capture, status, trial booking, notes; no automated follow-up sequences; tests | P0-15
- [ ] P1-16 | Complaint log (manual) | Complaint intake, status, assignee, resolution notes; tests | P0-15
- [ ] P1-17 | Equipment registry and manual maintenance schedules/reminders | Equipment records, manual maintenance schedules, reminder tasks/messages via mock with logging; no predictive maintenance; tests | P0-15, P0-14, P1-09

### 1.8 Staff panels (Owner/Admin/Reception/Trainer)
- [ ] P1-18 | Frontend scaffold and auth shell | React+Vite+TS+Tailwind app with routing, auth/login against backend, role-aware navigation for owner/admin/reception/trainer only; build/test/lint setup | P0-15
- [ ] P1-19 | Reception panel MVP | UI for member record entry/lookup, plan/membership actions, payments/dues, leads/trials, complaints; integrates APIs; smoke checks/tests where feasible | P1-02, P1-04, P1-06, P1-15, P1-16, P1-18
- [ ] P1-20 | Admin panel MVP | UI for plans, trainers, staff attendance/payroll records, expenses, equipment/maintenance; RBAC-respected; tests/smoke checks | P1-03, P1-11, P1-13, P1-14, P1-17, P1-18
- [ ] P1-21 | Owner dashboard MVP | UI for daily revenue/expense/profit, dues/expiries overview, key operational summaries; tests/smoke checks | P1-14, P1-18
- [ ] P1-22 | Trainer panel MVP | UI for assigned members, availability, sessions, trainer attendance; tests/smoke checks | P1-12, P1-18
- [ ] P1-23 | Phase 1 integration, docs, and hardening | End-to-end owner/staff flows pass (member record->plan->payment->reminder via mock->dashboard/CRM/complaints/equipment); docs/API updated; full suite green | P1-10, P1-19, P1-20, P1-21, P1-22

## Phase 2: AI WhatsApp chatbot (only AI feature)

- [ ] P2-01 | Inbound WhatsApp webhook and conversation store | Webhook endpoint receives inbound messages (mock/testable), stores conversations/messages with tenant/contact linkage; tests | P1-23, P0-11, P0-10
- [ ] P2-02 | Grounded gym knowledge source for chatbot | Structured access to gym data (timings, fees, plans, trainers, location/offers as available) used as sole grounding context; tests ensure answers derive from this data | P2-01, P1-03, P1-11
- [ ] P2-03 | Grounded FAQ answering with LLM interface and fallback | Chatbot answers FAQs using LLM interface when available, strictly grounded in gym data; falls back to canned replies + human handoff if LLM down/uncertain; no invented prices/promises; tests | P2-02, P0-13
- [ ] P2-04 | Trial booking and lead capture into CRM | Chatbot can capture lead details and create/update trial booking in leads CRM with consent-aware handling; tests | P2-03, P1-15
- [ ] P2-05 | Human handoff and staff inbox (bot pause/resume) | Escalation creates handoff, notifies/stores in staff inbox, bot paused while staff reply and resumable; tests for pause/resume and handoff flow | P2-03, P1-18
- [ ] P2-06 | Guardrails, rate limits, and conversation audit | Escalation keywords (medical/health/refunds/complaints/uncertainty) force handoff; per-number rate limits; full conversation and outbound reply audit log (who/what/why/template when applicable); tests | P2-05, P1-09
- [ ] P2-07 | Chatbot eval set | Eval tests with sample questions and expected grounded answers/handoffs covering timings, fees, plans, trainers, location, escalation cases, and LLM-down fallback; all pass | P2-06, P2-04
- [ ] P2-08 | Phase 2 integration and docs | Chatbot end-to-end with mock webhook/messaging/LLM, grounded answers, handoff/inbox, guardrails and audit verified; docs/API updated; full suite green | P2-07

## Phase 3: Multi-branch

- [ ] P3-01 | Owner dashboard across branches with comparison | Cross-branch aggregations for revenue/expense and key metrics with branch comparison views; tenant isolation enforced; tests | P2-08, P1-21
- [ ] P3-02 | Branch-level permissions | Permissions and data access scoped/enforced by branch per role rules; owner can view across branches as permitted; tests for allowed/denied access | P3-01, P0-09
- [ ] P3-03 | Phase 3 integration, docs, and release readiness | Multi-branch features integrated, docs/ADRs updated, full suite green, release summary | P3-02

## Maintenance (recurring every 5 iterations)
- [ ] MNT-01 | Refactor, dead-code cleanup, docs refresh, backlog reprioritization | Remove dead code, improve structure without behavior change, update README/API docs, re-prioritize backlog and record reasons in DECISIONS.md; tests remain green | recurring
