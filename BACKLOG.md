# GymOS — Backlog

Format: `- [ ] ID | title | acceptance criteria | deps`
Status legend: `[ ]` todo, `[x]` done, `[~]` blocked

## Phase 0: Foundation

- [x] P0-01 | Repo scaffold and base directories | `backend/`, `frontend/`, `infra/`, `docs/`, `.gitignore`, and top-level README exist; README describes stack and how to run locally | none
- [x] P0-02 | Backend project bootstrap (FastAPI + Python 3.12) | `backend/pyproject.toml` (or requirements) with FastAPI, SQLAlchemy 2, Alembic, Pydantic, pytest, lint/type tools; `backend/app/main.py` exposes `/health`; `pytest` runs at least one passing health test | P0-01
- [x] P0-03 | Docker Compose dev environment | `docker-compose.yml` defines api, db (Postgres), redis, worker services; `.env.example` provided; `docker compose config`/basic up instructions documented; local dev can start services (documented) | P0-02
- [ ] P0-04 | CI pipeline (GitHub Actions) | Workflow runs backend lint, type-check, and tests on push/PR; fails on errors; status documented in README | P0-02
- [ ] P0-05 | Linting and type-checking baseline | Ruff (or flake8+black) and mypy/pyright configured for backend with passing baseline; `make`/script commands or documented commands to run lint/type/test | P0-02
- [ ] P0-06 | Multi-tenant core schema and migrations | Alembic initialized; models/tables for gym, branch, user, role/user_role (or equivalent) all include `gym_id` and `branch_id` where applicable; migration applies cleanly to fresh DB; tests verify tenant columns present | P0-02
- [ ] P0-07 | Tenant scoping primitives | Base repository/service/query helpers enforce tenant scoping (gym_id/branch_id) and prevent cross-tenant access; tests prove queries cannot read/write other tenant data | P0-06
- [ ] P0-08 | Auth (JWT) and password handling | Register/login endpoints (or seed+login) issue JWT with user/tenant/role claims; password hashing; auth dependency extracts current user; tests cover success/failure/expiry basics | P0-06
- [ ] P0-09 | RBAC enforcement | Role-based access control for owner, admin, reception, trainer, member; decorator/dependency enforces permissions on protected endpoints; tests verify allowed/denied per role | P0-08
- [ ] P0-10 | Audit log foundation | Audit log table records actor, tenant, action, entity, timestamp, metadata/why; helper/service to write audit entries; tests verify audit records created for a sample privileged action | P0-07, P0-08
- [ ] P0-11 | Provider interface: messaging + mock | Messaging provider interface (send template/message, status hooks abstraction) with mock implementation storing sent messages in-memory/DB for tests; config selects mock by default; tests cover send and audit-friendly payload | P0-02
- [ ] P0-12 | Provider interface: payments + mock | Payments provider interface (create order/payment, record, webhook abstraction) with mock implementation; config selects mock by default; tests cover basic payment record flow | P0-02
- [ ] P0-13 | Provider interface: LLM + mock/rule fallback | LLM provider interface with mock implementation and explicit rule-based fallback path; feature flag/config to disable LLM; tests show graceful fallback when unavailable | P0-02
- [ ] P0-14 | Event bus / job scheduler baseline | Celery (or ARQ) worker configured with Redis; task registration and a sample scheduled/reminder task runs in dev/test mode; health/check mechanism and tests for task execution path | P0-03
- [ ] P0-15 | Foundation integration pass and docs | End-to-end smoke: start stack, run migrations, auth works, tenant scoping + RBAC enforced; README updated with setup, test, and architecture overview; all P0 tests green | P0-04, P0-05, P0-07, P0-09, P0-10, P0-11, P0-12, P0-13, P0-14

## Phase 1: Core Operations (MVP)

### 1.1 Members & Profiles
- [ ] P1-01 | Member model and registration API | Member entity (gym_id, branch_id, profile photo ref, KYC fields, emergency contact, health notes, consent flags) with create/read/update; validation; tests for tenant scoping and required fields | P0-15
- [ ] P1-02 | Auto profile creation flow | Registration flow auto-creates member profile and default status; audit log entry; tests cover happy path and duplicate handling | P1-01, P0-10

### 1.2 Memberships & Plans
- [ ] P1-03 | Membership plans CRUD | Plan entity (duration, price, benefits/limits metadata) scoped to gym/branch as appropriate; CRUD endpoints with RBAC; tests | P0-15
- [ ] P1-04 | Membership purchase, freeze, upgrade, expiry engine | Membership lifecycle states (active/frozen/expired/upgraded), purchase flow, freeze/unfreeze, upgrade rules, expiry calculation; scheduled/job or on-demand expiry processing; tests for transitions and expiry | P1-03, P0-14
- [ ] P1-05 | Receipts/invoices (GST-ready) data model | Invoice/receipt records with GST-relevant fields (configurable), linkage to payments/memberships; generation logic; tests for totals/tax fields | P1-04, P0-12

### 1.3 Attendance & Access
- [ ] P1-06 | Unique member QR generation (signed/rotating) | QR token generation per member with signature/rotation to prevent sharing; verification endpoint/service; tests for validity, expiry/rotation, and tamper rejection | P1-01
- [ ] P1-07 | Attendance check-in/out | Check-in/out records with timestamps, branch, method (QR/manual; NFC optional placeholder); duplicate-scan detection; tests | P1-06
- [ ] P1-08 | Shared-membership detection heuristics | Rule-based detection for suspicious sharing (e.g. rapid multi-location/duplicate patterns) with alerts/flags; tests with scenarios; no hardware assumptions | P1-07

### 1.4 Payments & Dues
- [ ] P1-09 | Payment recording (cash/UPI/card) and dues | Record payments via mock provider/manual modes, partial payments, dues calculation, late fee rules; tests for balances and edge cases | P1-05
- [ ] P1-10 | Payment receipts and reconciliation basics | Issue/lookup receipts, payment status tracking, basic reconciliation view data; tests | P1-09

### 1.5 WhatsApp & Messaging
- [ ] P1-11 | WhatsApp template management and consent/opt-out | Template storage/management, member consent and opt-out flags respected; approval/audit hooks for member-contact actions; tests ensure opt-out blocks send | P1-01, P0-11, P0-10
- [ ] P1-12 | Automated reminders (expiry 7/3/1, payment due, welcome) | Scheduler/jobs enqueue reminders based on rules; uses messaging mock; configurable auto-send vs staff-approve; audit log of who/what/why; tests for scheduling, content grounding, and approval flow | P1-04, P1-09, P1-11, P0-14

### 1.6 Trainers, Staff, Sessions
- [ ] P1-13 | Trainer profiles, availability, member assignment | Trainer entities, availability slots, assignment to members; RBAC; tests | P0-15
- [ ] P1-14 | Session booking and trainer attendance | Book/cancel/reschedule sessions, track trainer attendance; conflict/availability checks; tests | P1-13
- [ ] P1-15 | Staff attendance and payroll records | Staff attendance logs and payroll record structures (calculation-ready records, not live payroll disbursement); tests | P0-15

### 1.7 Expenses, Dashboard, CRM
- [ ] P1-16 | Expenses and daily revenue/expense/profit dashboard API | Expense tracking and aggregated metrics endpoints for daily revenue/expense/profit; tests for calculations | P1-09, P1-15
- [ ] P1-17 | Leads/enquiries CRM with trials and follow-ups | Lead capture, stages, trial booking, follow-up tasks/reminders; tests | P0-15, P0-14

### 1.8 Frontend & PWA (MVP surfaces)
- [ ] P1-18 | Frontend scaffold (React+Vite+TS+Tailwind) and auth shell | App bootstrapped with routing, auth/login flow against backend, role-aware navigation shells for owner/admin/reception/trainer/member; basic build/test/lint setup | P0-15
- [ ] P1-19 | Reception panel MVP | UI for member lookup/registration, check-in, payments/dues, lead/trial entry; integrates key APIs; smoke/e2e tests where feasible | P1-02, P1-07, P1-09, P1-17, P1-18
- [ ] P1-20 | Admin/Owner panel MVP | UI for plans, members, trainers, expenses, dashboard metrics; RBAC-respected views; tests/smoke checks | P1-03, P1-16, P1-18
- [ ] P1-21 | Trainer panel MVP | UI for assigned members, availability, sessions, attendance; tests/smoke checks | P1-14, P1-18
- [ ] P1-22 | Member PWA MVP | PWA shell showing membership status, QR code, schedule, payments/dues; installable basics and responsive UI; tests/smoke checks | P1-04, P1-06, P1-10, P1-14, P1-18
- [ ] P1-23 | Phase 1 integration, docs, and hardening | End-to-end MVP flows pass (register->plan->pay->QR check-in->reminders via mock->dashboard); docs/API updated; full suite green | P1-12, P1-19, P1-20, P1-21, P1-22

## Phase 2: AI Automation

- [ ] P2-01 | AI action approval/audit framework | Unified approval queue and audit logging for all AI actions that contact members or make recommendations; configurable auto-send vs staff-approve; tests | P1-23, P0-13, P0-10
- [ ] P2-02 | AI Gym Manager daily briefing | Daily briefing aggregates pending payments, expiring memberships, inactive members, complaints/issues with suggested actions and one-click approve; rule-based baseline + LLM enhancement behind interface; grounded in gym data; tests | P2-01, P1-16
- [ ] P2-03 | AI WhatsApp agent (grounded FAQs/booking/handoff) | Handles FAQs (timings, fees, plans), trial booking, lead capture with strict grounding in gym data, opt-out respect, and human handoff; mock messaging; tests for grounding and handoff | P2-01, P1-11, P1-17
- [ ] P2-04 | Inactive-member detection and re-engagement | Rules-first inactivity detection with configurable thresholds, transparent scoring fields, re-engagement flows via approval layer; tests | P2-01, P1-07
- [ ] P2-05 | Automated lead follow-up sequences | Configurable sequences for leads with scheduling, approval/audit, stop-on-conversion/opt-out; tests | P2-01, P1-17
- [ ] P2-06 | Workout plan generator and diet suggestions with safety controls | Generator produces plans/suggestions for trainer review before publishing; medical-condition flag forces trainer review; safety disclaimers included; LLM optional with rule/template fallback; tests | P2-01, P1-13
- [ ] P2-07 | Progress tracking (metrics, logs, charts) | Track weight/measurements/performance logs, APIs and UI charts; tests for calculations and tenant scoping | P1-23
- [ ] P2-08 | Complaint management with SLA and auto follow-ups | Complaint intake, SLA timers, status flow, auto follow-up tasks/messages via approval layer; tests | P2-01, P0-14
- [ ] P2-09 | Renewal prediction and retention alerts (transparent scoring) | Transparent scoring model (explainable factors, no black box) for renewal risk with alerts/actions; tests with deterministic fixtures | P2-01, P1-04
- [ ] P2-10 | Phase 2 integration and docs | AI features operate with mocks/fallbacks, approval/audit enforced, docs updated; full suite green | P2-02, P2-03, P2-04, P2-05, P2-06, P2-07, P2-08, P2-09

## Phase 3: Advanced

- [ ] P3-01 | Multi-branch owner dashboard and revenue comparison | Cross-branch aggregations (owner-scoped), comparisons, filters; tenant/branch isolation enforced; tests | P2-10
- [ ] P3-02 | Live occupancy and peak-hour analytics | Occupancy derived from attendance check-in/out data, peak-hour analytics views; tests | P2-10, P1-07
- [ ] P3-03 | Equipment registry and maintenance schedules | Equipment records, maintenance schedules, issue alerts; predictive only when sufficient data exists (guarded); tests | P2-10
- [ ] P3-04 | Demand/revenue forecasting | Forecasting module with transparent assumptions, baseline/statistical methods; reports; tests on deterministic/sample data | P3-01
- [ ] P3-05 | AI business recommendations | Recommendations generated from metrics with explainability and approval/audit where actions contact members; graceful fallback; tests | P3-04, P2-01
- [ ] P3-06 | Optional face check-in (consent-gated) + hardware integration docs | Consent-gated opt-in flow, store embeddings not photos, interface + mock/simulator; hardware integration docs and BLOCKERS for real devices/SDKs; never claim real biometrics work without hardware | P2-10, P1-07
- [ ] P3-07 | Phase 3 integration, docs, and release readiness | Advanced features integrated behind flags where needed, docs/ADRs updated, full suite green, release summary | P3-01, P3-02, P3-03, P3-04, P3-05, P3-06

## Maintenance (recurring every 5 iterations)
- [ ] MNT-01 | Refactor, dead-code cleanup, docs refresh, backlog reprioritization | Remove dead code, improve structure without behavior change, update README/API docs, re-prioritize backlog and record reasons in DECISIONS.md; tests remain green | recurring
