# GymOS — Progress Log (append-only)

## Iteration 0 (setup)
- Task: Initialize state files and backlog
- Changes: Created PLAN.md, BACKLOG.md, PROGRESS.md, DECISIONS.md, BLOCKERS.md, docs/adr/
- Tests: N/A (no codebase yet)
- Status: State initialized, beginning Phase 0 iteration 1
- Known issues: None

## Iteration 1
- Task: P0-01 | Repo scaffold and base directories
- Changes: Added `backend/`, `frontend/`, `infra/` directories; created `.gitignore` and `README.md` (stack + local run instructions); added `tests/test_p0_01_scaffold.py`; initialized git repo.
- Tests: `python -m pytest -q tests/test_p0_01_scaffold.py` -> `3 passed in 0.03s` (exit 0). Baseline suite: same 3 tests, all passing.
- Status: Done, committed.
- Known issues: None

## Iteration 2
- Task: P0-02 | Backend project bootstrap (FastAPI + Python 3.12)
- Changes: Added `backend/pyproject.toml` with FastAPI, SQLAlchemy 2, Alembic, Pydantic, psycopg, redis, celery, pytest/ruff/mypy config; created `backend/app/main.py` with `/health`; added `backend/tests/test_p0_02_bootstrap.py`; installed core dev deps in environment for test execution.
- Tests: `(cd backend && python -m pytest -q tests/test_p0_02_bootstrap.py)` -> `2 passed, 1 warning in 0.29s` (exit 0, StarletteDeprecationWarning about httpx in TestClient). Regression: `python -m pytest -q tests/test_p0_01_scaffold.py` -> `3 passed in 0.02s` (exit 0).
- Status: Done, committed.
- Known issues: Starlette/TestClient deprecation warning (non-blocking); can pin/adjust httpx stack later if needed.

## Iteration 3
- Task: P0-03 | Docker Compose dev environment
- Changes: Added `docker-compose.yml` (api, db/Postgres, redis, worker services with healthchecks/volumes), `.env.example` (core vars, provider toggles, placeholders for WhatsApp/Razorpay noted in BLOCKERS), and `backend/Dockerfile`; README already documents `docker compose up`.
- Tests: `python -m pytest -q tests/test_p0_03_compose.py tests/test_p0_01_scaffold.py` -> `6 passed in 0.04s` (exit 0). Backend suite: `(cd backend && python -m pytest -q)` -> `2 passed, 1 warning` (exit 0, same StarletteDeprecationWarning). `docker compose config` not executed here (Docker runtime not verified in this session); compose file authored per spec and instructions documented.
- Status: Done, committed.
- Known issues: Worker command expects `app.worker.celery_app` (to be added in P0-14); Docker daemon/startup not validated in-session.

## Iteration 4
- Task: Scope re-alignment (owner/staff-only, WhatsApp chatbot as only AI) + baseline verification
- Changes: Rewrote `PLAN.md`, `BACKLOG.md`, `README.md` to match hard scope boundaries (OUT items removed: member app/PWA/login, QR/NFC/member attendance/shared-detection, non-chatbot AI features, face/forecasting/occupancy, etc.); updated roles to owner/admin/reception/trainer only; revised Phase 2 to chatbot-only and Phase 3 to multi-branch dashboard+permissions; updated `DECISIONS.md` and `BLOCKERS.md` (dropped BLK-003 biometric/NFC hardware). Preserved completed P0-01..P0-03.
- Tests (baseline, no regressions): `python -m pytest -q tests` -> `6 passed in 0.03s` (exit 0). `(cd backend && python -m pytest -q)` -> `2 passed, 1 warning in ~1s` (exit 0, StarletteDeprecationWarning via TestClient/httpx).
- Status: State aligned; ready to continue Phase 0.
- Known issues: Same as prior (Starlette/TestClient deprecation warning; worker app path pending P0-14; Docker runtime not validated).

## Iteration 5
- Task: P0-04 | CI pipeline (GitHub Actions)
- Changes: Added `.github/workflows/ci.yml` to run backend lint (ruff), type-check (mypy), and tests (pytest) on push/PR (Python 3.12, `backend` working dir); added `tests/test_p0_04_ci.py`; README already documents GitHub Actions/CI.
- Tests: `python -m pytest -q` (root, includes backend tests discovery path via run context shown) -> `10 passed, 1 warning in 0.33s` (exit 0). `(cd backend && python -m pytest -q)` -> `2 passed, 1 warning` (exit 0). Same StarletteDeprecationWarning observed. Lint/type commands in CI not executed locally this iteration (P0-05 will establish passing baseline).
- Status: Done, committed.
- Known issues: ruff/mypy may not yet pass on full backend until P0-05 baseline/config fixes applied.

## Iteration 6
- Task: P0-05 | Linting and type-checking baseline
- Changes: Fixed ruff issues in `backend/tests/test_p0_02_bootstrap.py` (`ruff check . --fix`: import order, `getattr` -> attribute access); updated `README.md` with backend quality commands (ruff/mypy/pytest) and CI note; added `tests/test_p0_05_lint_type.py`.
- Tests: `python -m pytest -q` (root) -> `13 passed, 1 warning in 1.36s` (exit 0). `(cd backend && python -m pytest -q)` -> `2 passed, 1 warning` (exit 0). Verified passing baseline: `ruff check .` exit 0, `mypy app` exit 0 (`Success: no issues found in 2 source files`).
- Status: Done, committed.
- Known issues: Same StarletteDeprecationWarning (non-blocking).

## Iteration 7
- Task: P0-06 | Multi-tenant core schema and migrations
- Changes: Added `app/core/config.py`, `app/db/base.py`, core tenant models (`gyms`, `branches`, `users`, `roles`) with `gym_id`/`branch_id` on all tables; initialized Alembic and configured `alembic/env.py` + `alembic.ini`; generated and applied-ready migration `a5fe0e8cbbca_core_tenant_schema.py`; added `backend/tests/test_p0_06_schema.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `5 passed, 1 warning` (exit 0). Root: `python -m pytest -q` -> `16 passed, 1 warning in 2.09s` (exit 0). Lint/type: `(cd backend && ruff check .)` exit 0, `(cd backend && mypy app)` -> `Success: no issues found in 8 source files` (exit 0). Migration test applies to fresh SQLite DB via Alembic upgrade head.
- Status: Done, committed.
- Known issues: SQLite used for migration test speed; Postgres compatibility to be validated in integration/docker flows later.

## Iteration 8
- Task: P0-07 | Tenant scoping primitives
- Changes: Added `app/db/tenant.py` (`scoped_query`, `tenant_add`, `assert_tenant_match`, `TenantScopeError`) and `app/db/session.py`; added `backend/tests/test_p0_07_tenant_scope.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `8 passed, 1 warning` (exit 0). Lint/type: `(cd backend && ruff check .)` exit 0, `(cd backend && mypy app)` -> `Success: no issues found in 10 source files` (exit 0).
- Status: Done, committed.
- Known issues: None.

## Iteration 9
- Task: P0-08 | Auth (JWT) and password handling
- Changes: Added `app/core/security.py` (bcrypt hashing, JWT create/decode), `app/api/deps.py` (Bearer auth + current user with tenant/role resolution), `app/api/routes/auth.py` (`POST /auth/login`, `GET /auth/me`), wired router in `app/main.py`; added `UserRole` model/migration `64d2179d570d_add_user_roles.py`; added `backend/tests/test_p0_08_auth.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `11 passed, 1 warning` (exit 0). Lint/type: `(cd backend && ruff check .)` exit 0, `(cd backend && mypy app)` -> `Success: no issues found in 15 source files` (exit 0).
- Status: Done, committed.
- Known issues: StarletteDeprecationWarning persists (non-blocking). Login requires gym_id in payload (tenant-explicit) for multi-tenant scoping.

## Iteration 10 (maintenance pass included)
- Task: P0-09 | RBAC enforcement
- Changes: Added `app/core/rbac.py` (`require_roles` dependency) enforcing allowed roles (owner/admin/reception/trainer) with 403 on denial; added `backend/tests/test_p0_09_rbac.py` (owner-only allow/deny, all staff roles allowed, unauthenticated 401).
- Maintenance (every 5 iterations): verified lint/type/test baseline clean; updated README with backend quality commands previously and confirmed docs consistent; backlog reprioritized implicitly (next: P0-10 audit log, then P0-11..P0-14 providers/scheduler, P0-15 integration). No dead code removed this pass.
- Tests: `(cd backend && python -m pytest -q)` -> `14 passed, 1 warning` (exit 0). Root: `python -m pytest -q` -> `25 passed, 1 warning` (exit 0, observed in prior runs + this iteration). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 16 source files` (exit 0).
- Status: Done, committed.
- Known issues: Same deprecation warning; alembic version files may need periodic `ruff --fix` (consider exclude/hook later).

## Iteration 11
- Task: P0-10 | Audit log foundation
- Changes: Added `AuditLog` model (`audit_logs` with actor/tenant/action/entity/timestamp/metadata/why), `app/services/audit.py` (`write_audit_log`), model/env registration, migration `681fa42340de_add_audit_logs.py`; added `backend/tests/test_p0_10_audit.py` (note: test file was committed early in iteration 10 commit but implemented/fixed this iteration).
- Tests: `(cd backend && python -m pytest -q)` -> `15 passed, 1 warning` (exit 0). Root: `python -m pytest -q` -> `26 passed, 1 warning in 6.49s` (exit 0). Lint/type: `ruff check .` exit 0 (after fix), `mypy app` -> `Success: no issues found in 19 source files` (exit 0).
- Status: Done, committed.
- Known issues: Audit `metadata` stored as JSON column (`metadata_json` attribute) for SQLite/Postgres compatibility.

## Iteration 12
- Task: P0-11 | Provider interface: messaging + mock
- Changes: Added `app/providers/messaging.py` with `MessagingProvider` protocol, `MockMessagingProvider` (stores sent template/message records with audit payload who/what/why/template), and `get_messaging_provider()` defaulting to mock; added `backend/tests/test_p0_11_messaging_provider.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `17 passed, 1 warning` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 21 source files` (exit 0).
- Status: Done, committed.
- Known issues: Real WhatsApp provider raises NotImplementedError without credentials (BLK-001); mock only.

## Iteration 13
- Task: P0-12 | Provider interface: payments + mock
- Changes: Added `app/providers/payments.py` with `PaymentsProvider` protocol, `MockPaymentsProvider` (create/record payment flow), and `get_payments_provider()` defaulting to mock; added/implemented `backend/tests/test_p0_12_payments_provider.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `19 passed, 1 warning` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 22 source files` (exit 0).
- Status: Done, committed.
- Known issues: Real Razorpay/UPI provider raises NotImplementedError without credentials (BLK-002); mock only.

## Iteration 14
- Task: P0-13 | Provider interface: LLM + mock and canned fallback
- Changes: Added `app/providers/llm.py` with `LLMProvider` protocol, `MockLLMProvider` (chatbot-only mock), `CannedFallbackLLMProvider` (canned reply + human handoff), and `get_llm_provider()` falling back when `LLM_ENABLED` is false/unavailable; added `backend/tests/test_p0_13_llm_provider.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `22 passed, 1 warning` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 23 source files` (exit 0).
- Status: Done, committed.
- Known issues: Real LLM provider not implemented without credentials (BLK-004); defaults to safe fallback when disabled.

## Iteration 15 (maintenance pass included)
- Task: P0-14 | Job scheduler for reminders & P0-15 | Foundation integration pass and docs
- Changes: Added `app/worker.py` (Celery app + `sample_reminder_task`) and `backend/tests/test_p0_14_scheduler.py`; added `backend/tests/test_p0_15_foundation_smoke.py` (auth, RBAC, tenant scoping, audit, provider mocks wired); updated `README.md` with foundation status. Maintenance: re-verified full lint/type/test baseline and docs; backlog shows Phase 0 complete.
- Tests: `(cd backend && python -m pytest -q)` -> `25 passed, 1 warning` (exit 0). Root: `python -m pytest -q` -> `36 passed, 1 warning in 7.74s` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 24 source files` (exit 0). Smoke validates migrations/schema usage, auth/JWT claims, RBAC allow/deny, tenant isolation, audit write, and mock providers/fallback.
- Status: Done, committed. Phase 0 complete.
- Known issues: StarletteDeprecationWarning (non-blocking); Docker runtime not validated in-session; SQLite used in tests (Postgres integration pending docker/runtime validation); real WhatsApp/Razorpay/LLM blocked by credentials (mocks/fallback in place).

## Iteration 16
- Task: Integration direction update (user directive)
- Changes: Adopted **openWA** (wa-automate-nodejs) as WhatsApp integration target and **YouPI-PG** as payments integration target; **LLM and other components remain unchanged**. Added ADRs `docs/adr/0001-messaging-integration-openwa.md` and `docs/adr/0002-payments-integration-youpi-pg.md`; updated `PLAN.md`, `README.md`, `.env.example`, `DECISIONS.md`, `BLOCKERS.md` (BLK-001/BLK-002 revised), and backlog wording for messaging templates/reminders to stay compatible with openWA while preserving consent/opt-out/logging requirements.
- Tests (regression, no code logic changes): `python -m pytest -q` (root) -> `36 passed, 1 warning` (exit 0). StarletteDeprecationWarning only.
- Status: State/decision aligned; provider interfaces remain mock-default until real openWA/YouPI-PG setup available.
- Known issues: openWA is unofficial WhatsApp Web automation (session/ToS/ops risks); YouPI-PG is experimental/self-hosted with reconciliation/compliance considerations; no real integrations configured or claimed.

## Iteration 17
- Task: P1-01 | Member record model and CRUD
- Changes: Added `Member` model (`members` with gym_id/branch_id, profile photo ref, KYC fields, emergency contact, health notes, WhatsApp consent/opt-out, active flag), migration `1d371e524076_add_members.py`, and API routes `POST/GET/PATCH /members` with tenant scoping and RBAC (write: owner/admin/reception, read: owner/admin/reception/trainer); added `backend/tests/test_p1_01_members.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `27 passed, 1 warning` (exit 0). Root: `python -m pytest -q` -> `38 passed, 1 warning in 9.76s` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 26 source files` (exit 0).
- Status: Done, committed.
- Known issues: Member create defaults `branch_id` to current user's branch (or 0 if unset); further branch-assignment rules can be refined in later tasks. Bcrypt/passlib version warning observed in test logs (non-failing).

## Iteration 18
- Task: P1-02 | Member record audit and data handling
- Changes: `members` create/update now write audit log entries (`member.create`, `member.update`) via `write_audit_log` with actor/tenant/entity context; update metadata logs changed field names only (no sensitive values). Added `backend/tests/test_p1_02_member_audit.py`.
- Tests: `(cd backend && python -m pytest -q tests/test_p1_02_member_audit.py)` -> `1 passed, 1 warning` (exit 0). Full backend: `(cd backend && python -m pytest -q)` -> `28 passed, 1 warning` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 26 source files` (exit 0).
- Status: Done, committed.
- Known issues: Audit metadata includes changed field names; ensure future sensitive fields remain value-redacted.

## Iteration 19
- Task: P1-03 | Membership plans CRUD
- Changes: Added `MembershipPlan` model (`membership_plans`: name, duration_days, price_paise, currency, terms JSON, is_active) with migration `77ca8d6edcbf_add_membership_plans.py`; added `POST/GET/PATCH /plans` routes with tenant scoping and RBAC (write: owner/admin, read: all staff); added `backend/tests/test_p1_03_plans.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `30 passed, 1 warning` (exit 0). Root: `python -m pytest -q` -> `41 passed, 1 warning in 16.26s` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 28 source files` (exit 0).
- Status: Done, committed.
- Known issues: Plan branch defaults to user's branch (or 0); plan deletion not implemented (use is_active). StarletteDeprecationWarning and bcrypt/passlib log warning persist (non-failing).

## Iteration 20 (maintenance pass included)
- Task: P1-04 | Membership purchase, freeze, upgrade, expiry engine
- Changes: Added `Membership` model/migration `d2a893468c05_add_memberships.py` (active/frozen/expired/upgraded states, freeze/upgrade tracking), `app/services/memberships.py` (`expire_due_memberships`), and routes for purchase, get, freeze/unfreeze (extends end_date by frozen days), upgrade (marks old upgraded, creates new), and on-demand expiry run; wired router in app. Added `backend/tests/test_p1_04_memberships.py`.
- Maintenance (every 5 iterations): re-verified full lint/type/test baseline, ruff-fixed generated migration, backlog/state consistent (next: P1-05 receipts/GST-ready invoices, then P1-06 payments/dues). No dead code removed.
- Tests: `(cd backend && python -m pytest -q)` -> `32 passed, 1 warning` (exit 0). Root: `python -m pytest -q` -> `43 passed, 1 warning` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 31 source files` (exit 0).
- Status: Done, committed.
- Known issues: Expiry engine callable on-demand/service-level (Celery schedule wiring for periodic expiry can be added in reminder/scheduler tasks later); upgrade starts new plan duration from provided start date (proration rules not implemented). Same warnings as before.

## Iteration 21
- Task: P1-05 | Receipts and GST-ready invoices
- Changes: Added `Invoice` model/migration `c5a7b7e28705_add_invoices.py` (GST fields: taxable value, rate, CGST/SGST/IGST, total, configurable seller/buyer/metadata, linked to member/membership/payment), `app/services/invoices.py` (`generate_invoice` with intra/inter GST split), and `POST/GET /invoices` routes with tenant scoping/RBAC. Added `backend/tests/test_p1_05_invoices.py`.
- Tests: `(cd backend && python -m pytest -q)` -> `34 passed, 1 warning` (exit 0). Root: `python -m pytest -q` -> `45 passed, 1 warning` (exit 0). Lint/type: `ruff check .` exit 0, `mypy app` -> `Success: no issues found in 34 source files` (exit 0).
- Status: Done, committed.
- Known issues: Invoice numbering is simple per-gym sequence; `payment_id` linkage will be exercised in P1-06+. GST logic is configurable/basic (intra CGST/SGST split, inter IGST) and may need jurisdiction-specific refinement.


## Iteration 22
- Task: P1-06 | Payment recording and dues
- Changes: Added `Payment` model/migration `879200a8a868_add_payments_and_invoice_late_fee.py` (cash/upi/card/mock, amount, reference, status, invoice/membership linkage, recorded_by), `app/services/payments.py` (record_payment, invoice due/paid aggregation, invoice status sync paid/partial/issued, late fee application, member_dues), `POST /payments`, `GET /payments/dues`, `POST /invoices/{id}/late-fee`; added `late_fee_paise` to invoices. Added `backend/tests/test_p1_06_payments.py` (partial->full, overpayment clamp, API flow, invalid method/amount, late fee, cross-tenant block).
- Tests: backend `python -m pytest -q` -> 39 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 37 source files. Migration upgrade/downgrade/upgrade verified on SQLite.
- Status: Done, committed.
- Known issues: Payment statuses limited to recorded 'paid' (no provider async states yet); overpayment is accepted but not credited/refunded; late fee is manual per invoice (no aging rules). YouPI-PG remains mock/blocked (BLK-002).

## Iteration 23
- Task: P1-07 | Payment receipts lookup and status
- Changes: Added `GET /payments` (member filter, capped limit), `GET /payments/{id}/receipt` (receipt number `RCPT-{gym}-{payment:06d}`, payment/invoice/member snapshot), `POST /payments/{id}/status` (paid/pending/failed/refunded, owner/admin/reception) with invoice status + dues resync; service `update_payment_status`. Added `backend/tests/test_p1_07_receipts.py` (receipt lookup/list, refund reopens dues, cross-tenant isolation, invalid status 422).
- Tests: backend `python -m pytest` -> 42 passed, 1 warning (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 37 source files.
- Status: Done, committed.
- Known issues: Receipts are JSON only (no PDF); status changes are manual until provider webhooks exist (BLK-002). No refunds ledger/payout reconciliation.

## Iteration 24
- Task: P1-08 | WhatsApp template/message management and opt-out
- Changes: Added `MessageTemplate` model/migration `314b28b427f5_add_message_templates.py` (name/body/category/is_active, unique name per gym), `POST/GET/PATCH /message-templates` (owner/admin write, staff read), and `app/services/messaging.py` (`render_template` with missing-param errors, `send_template_to_member` enforcing consent + opt-out before provider call, holds `OptOutError`). Added `backend/tests/test_p1_08_templates.py` (CRUD, rendered send, opt-out/no-consent blocked, missing params).
- Tests: backend `python -m pytest` -> 44 passed, 1 warning (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 40 source files. Migration autogenerated and ruff-fixed.
- Status: Done, committed.
- Known issues: Sending is service-level only (no send endpoint yet; P1-09 logging + P1-10 reminders will expose it). WhatsApp template approval categories are local metadata; openWA/Meta approval flow remains blocked (BLK-001).

## Iteration 25
- Task: P1-09 | Outbound message logging and audit
- Changes: Added `OutboundMessage` model/migration `dc7f37b00346_add_outbound_messages.py` (member/phone/template/body/kind/status/provider/who/why/error/created_at), `GET /messages` with member/status filters, and `send_logged_template` which persists an audit row for every outcome (sent, blocked by consent/opt-out, failed render/provider) and stores who/what/why/template. Added `backend/tests/test_p1_09_outbound_messages.py`.
- Tests: backend `python -m pytest` -> 47 passed, 1 warning (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 42 source files.
- Status: Done, committed.
- Known issues: Logs are outbound-only (inbound arrives P2-01); no retry/backoff for failed sends; openWA delivery receipts unavailable until BLK-001 clears.

## Iteration 26 (maintenance pass included)
- Task: P1-10 | Automated reminders (welcome, expiry 7/3/1, payment due)
- Changes: Added `app/services/reminders.py` (template-driven welcome on start date, expiry at 7/3/1 days, payment due for issued/partial invoices; per-day idempotency via `why` keys; opt-out handled by logged-send service), `POST /reminders/run` (owner/admin, on-demand with date override), and Celery `run_reminders_task`. Added `backend/tests/test_p1_10_reminders.py` (send once, opt-out blocked, API run + idempotency).
- Maintenance (every 5 iterations): full lint/type/test re-verified; reminder idempotency keyed by date+entity; backlog next is P1-11 trainers. No dead code removed.
- Tests: backend `python -m pytest` -> 49 passed, 1 warning (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 44 source files. No schema change.
- Status: Done, committed.
- Known issues: Celery beat schedule not yet configured for daily runs (task callable/on-demand endpoint works); reminders require templates named `welcome`/`expiry_reminder`/`payment_due`; openWA delivery remains mocked (BLK-001).

## Iteration 27
- Task: P1-11 | Trainer profiles, availability, member assignment
- Changes: Added `Trainer`/`TrainerAvailability`/`TrainerAssignment` models + migration `2014cf4e09f5_add_trainers_availability_assignments.py`; `POST/GET/PATCH /trainers`, weekly availability add/list/delete with start<end validation, member assign/list/unassign with duplicate (409) and tenant isolation. RBAC: owner/admin write, all staff read. Added `backend/tests/test_p1_11_trainers.py`.
- Maintenance fixes: added Celery beat schedule + `run_all_gyms_reminders_task` / `expire_all_gyms_task` and a `beat` compose service; excluded generated `alembic/versions` from ruff; filtered the known third-party Starlette testclient deprecation; replaced deprecated 422 constant.
- Tests: backend `python -m pytest` -> 51 passed (exit 0, warning filtered). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 46 source files.
- Status: Done, committed.
- Known issues: Trainer availability is recurring weekly only (no date exceptions); trainer user linkage is optional and not validated against the trainer role yet; assignment has no history/audit beyond is_active.

## Iteration 28
- Task: P1-12 | Session booking and trainer attendance
- Changes: Added `TrainingSession`/`TrainerAttendance` models + migration `19a9fa4259a4_add_training_sessions_and_trainer_.py`; `POST/GET /sessions`, `POST /sessions/{id}/reschedule`, `POST /sessions/{id}/cancel`, `POST /sessions/{id}/attendance`, `GET /sessions/{id}/attendance`. Booking validates window ordering, weekly availability coverage (if configured), trainer and member overlap conflicts, tenant scoping; attendance marks session completed. Added `backend/tests/test_p1_12_sessions.py`.
- Tests: backend `python -m pytest` -> 54 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 48 source files.
- Status: Done, committed.
- Known issues: Sessions use naive local datetimes (no timezone conversion); availability is weekly recurring without exceptions; no calendar feed/notifications; attendance is a single check-in/out pair per session.

## Iteration 29
- Task: P1-13 | Staff attendance (manual by admin) and payroll records
- Changes: Added `StaffAttendance`/`PayrollRecord` models + migration `b2816c717694_add_staff_attendance_and_payroll.py`; owner/admin-only `POST/GET /staff-attendance` (duplicate day 409, time-order validation, month filter) and `POST/GET /payroll` + `POST /payroll/{id}/finalize` (net = base + bonus - deductions, one record per user/month, draft->finalized). Added `backend/tests/test_p1_13_staff.py`.
- Tests: backend `python -m pytest` -> 56 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 50 source files.
- Status: Done, committed.
- Known issues: No payroll disbursement/payslips/tax (calculation-ready records only, as scoped); no attendance edit/delete; attendance is manual only.

## Iteration 30
- Task: P1-14 | Expenses and daily revenue/expense/profit dashboard API
- Changes: Added `Expense` model + migration `4b150da02ccc_add_expenses.py`; owner/admin `POST/GET /expenses` (month/date/category filters) and `GET /dashboard/daily` + `GET /dashboard/summary` computing paid revenue (refunded excluded), expenses and profit; added `backend/tests/test_p1_14_dashboard.py`.
- Tests: backend `python -m pytest` -> 58 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 52 source files.
- Status: Done, committed.
- Known issues: Dashboard is tenant-wide (branch breakdown arrives P3-01); revenue is cash-basis from recorded payments only; expenses have no edit/delete/approval flow.

## Iteration 31
- Task: P1-15 | Leads/enquiries CRM
- Changes: Added `Lead` model + migration `844fb3504dce_add_leads.py`; `POST/GET/GET-by-id/PATCH /leads` with pipeline statuses new/contacted/trial_booked/converted/lost, trial date, assignee, source, notes; status filter via `?status=`; reception write, all staff read, tenant-scoped. Added `backend/tests/test_p1_15_leads.py`.
- Tests: backend `python -m pytest` -> 60 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 54 source files.
- Status: Done, committed.
- Known issues: No lead follow-up automation (explicitly OUT of scope); no lead-to-member conversion record linking; no duplicate-phone detection.

## Iteration 32
- Task: P1-16 | Complaint log (manual)
- Changes: Added `Complaint` model + migration `c775e48f3f8e_add_complaints.py`; `POST/GET/GET-by-id/PATCH /complaints` with statuses open/in_progress/resolved/closed, optional member linkage, assignee, resolution notes (required to resolve/close), `?status=` filter, tenant scoping; reception write, all staff read. Added `backend/tests/test_p1_16_complaints.py`.
- Tests: backend `python -m pytest` -> 62 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 56 source files.
- Status: Done, committed.
- Known issues: No SLA/escalation timers or notifications; complaint resolution does not notify the member; no file attachments.

## Iteration 33
- Task: P1-17 | Equipment registry and manual maintenance schedules/reminders
- Changes: Added `Equipment`/`MaintenanceSchedule` models + migration `1cdb7fe0e6ec_add_equipment_and_maintenance.py`; owner/admin equipment CRUD-ish endpoints (create/list/get/update status), maintenance scheduling per equipment, due list (defaults to scheduled), completion that optionally spawns the next occurrence by `interval_days`, and `POST /maintenance/run-reminders`. Added `send_logged_message` for non-member internal notices and `run_maintenance_reminders` (3-day window, per-day idempotency, logged via mock provider); Celery beat task `run_maintenance_reminders_task`. Added `backend/tests/test_p1_17_equipment.py`.
- Tests: backend `python -m pytest` -> 66 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 59 source files.
- Status: Done, committed.
- Known issues: Reminders target an internal `gym-staff` pseudo-recipient (no staff phone model); no predictive maintenance or parts inventory; no maintenance cost tracking.

## Iteration 34
- Task: Supporting list endpoints for frontend panels (P1-19/P1-20/P1-21 prerequisites)
- Changes: Added `GET /members` (`q` name/phone search, `is_active`), `GET /memberships` (`member_id`, `status`), `GET /invoices` (`member_id`, `status`); all tenant-scoped and return `{items,total}` with a 200-row cap. Added `backend/tests/test_list_endpoints.py`.
- Tests: backend `python -m pytest` -> 68 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 59 source files.
- Status: Done, committed.
- Known issues: No pagination offset/cursor yet; `/plans` still returns a bare array for backwards compatibility.

## Iteration 35
- Task: P1-18..P1-22 | Frontend scaffold, auth shell, and staff panels MVP (Reception, Admin, Owner, Trainer)
- Changes:
  - Initialized React 18 + Vite + TypeScript + Tailwind CSS application in `frontend/`.
  - Added `api.ts` client wrapper supporting JWT auth, error extraction, and response normalization for both plain arrays and `{items, total}` paginated lists.
  - Implemented `AuthContext` with JWT decoding, localStorage persistence, multi-role switcher, and role guards (`hasRole`).
  - Added `ProtectedRoute`, `Navbar`, and `Sidebar` with role-aware navigation (Owner, Admin, Reception, Trainer).
  - Implemented full staff panels:
    - `Login.tsx`: Gym ID, email, password, and quick demo credentials presets.
    - `ReceptionPanel.tsx`: Searchable member directory, new member registration modal with KYC and WhatsApp opt-in, plan enrollment modal, and payment recording modal with dues lookup.
    - `AdminPanel.tsx`: Membership plans management (active/inactive toggle, plan creation), manual staff attendance roster, expense logging, and equipment maintenance schedules.
    - `OwnerDashboard.tsx`: Executive revenue, active memberships, pending dues, automated WhatsApp reminder engine status, and recent invoice stream.
    - `TrainerPanel.tsx`: Assigned members roster with medical/health notes, daily session schedule with completion toggles, and trainer check-in.
  - Configured Playwright E2E suite (`playwright.config.ts`, `tests/e2e/auth-and-panels.spec.ts`).
  - Added root test `tests/test_p1_18_frontend.py` verifying frontend structure, dependencies, configs, and panels.
- Tests:
  - `npm run build` -> built in 36.40s, exit code 0 (`dist/` generated, 0 TypeScript errors).
  - `npm run lint` (`tsc --noEmit`) -> exit code 0.
  - `python -m pytest tests/test_p1_18_frontend.py` -> 5 passed in 0.24s (exit 0).
  - Root suite -> 13 passed in 0.25s (exit 0).
- Status: Done. "Frontend not started" issue resolved.
- Known issues: E2E Playwright tests require running Vite dev server + live backend; frontend UI styling uses Tailwind CSS.

## Iteration 35
- Task: P1-18..P1-22 Frontend panels wired to real backend APIs
- Changes: Fixed frontend API client (`api.ts`) to unwrap `{items,total}` lists, match real payment response shape (`PaymentResult`), freeze/unfreeze payloads (`frozen_on`/`unfrozen_on`), and added `ops.ts` types for leads, complaints, equipment, maintenance, trainers, sessions, staff, finance. Updated `ReceptionPanel` with tabs for leads/complaints using new `LeadsBoard`/`ComplaintsBoard` components. Rewrote `AdminPanel` against real endpoints (plans, trainers, staff attendance/payroll, expenses, equipment/maintenance). Rewrote `OwnerDashboard` with live daily/monthly finance summaries, dues, expiries, pipeline. Rewrote `TrainerPanel` with availability, assigned members, today's sessions, attendance check-in (trainer can mark own sessions). Added `/users` list endpoint for staff names, trainer attendance permission fix (trainers can record own sessions). Added `test_users_list.py` and `test_p1_22_trainer_attendance.py`.
- Tests: backend `python -m pytest` -> 72 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 60 source files. Frontend `npm run build` -> success. `npm run test:e2e` -> 3 passed (auth/panels smoke).
- Status: Done, committed.

## Iteration 36
- Task: P1-23 | Phase 1 integration, docs, and hardening
- Changes: Full backend test suite (72 tests) passes with 0 failures. Ruff + mypy clean. Frontend builds successfully and Playwright E2E smoke tests (auth + panel navigation) pass 3/3. All P1 panel APIs are wired and working against the real backend contracts.
- Tests: backend `python -m pytest` -> 72 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 60 source files. Frontend `npm run build` -> success. `npm run test:e2e` -> 3 passed (auth/panels smoke).
- Status: Phase 1 complete. Next: Phase 2 (P2-01..P2-08) WhatsApp chatbot integration.

## Iteration 37
- Task: P2-01 | Inbound WhatsApp webhook and conversation store
- Changes: Added `Conversation`/`InboundMessage` models + migration `141ef34464af_add_conversations_and_inbound_messages.py`; `POST /whatsapp/webhook` accepts inbound messages (JSON/form), creates/updates conversation per contact, logs raw payload; `GET /whatsapp/conversations` with status filter; `GET /whatsapp/conversations/{id}/messages` for history; `POST /whatsapp/conversations/{id}/pause|resume` for bot pause/resume; `PATCH /whatsapp/conversations/{id}` for status/bot_paused updates. RBAC: owner/admin/reception can read/manage, trainer cannot. Added `tests/test_p2_01_whatsapp_webhook.py` (6 tests).
- Tests: backend `python -m pytest` -> 78 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 62 source files.
- Status: Done, committed.
- Known issues: Signature validation not yet implemented (header reserved); per-number rate limiting not yet added; webhook assumes single gym in dev (gym_id inferred).

## Iteration 38
- Task: P2-02 | Grounded gym knowledge source for chatbot
- Changes: Added `app/services/knowledge.py` with `get_gym_knowledge()` fetching structured data (plans, trainers with availability, branch info), `format_knowledge_for_llm()` rendering concise text block for LLM system prompt, and `get_member_context()` for personalized member data (active membership, dues). Models: `PlanInfo`, `TrainerInfo`, `BranchInfo`, `GymKnowledge` dataclasses. Handles dict-type plan terms. Added `tests/test_p2_02_knowledge.py` (6 tests).
- Tests: backend `python -m pytest` -> 84 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 63 source files.
- Status: Done, committed.

## Iteration 39
- Task: P2-03 | Grounded FAQ answering with LLM interface and fallback
- Changes: Added `app/services/chatbot.py` with `run_chatbot()` that: (1) checks guardrail keywords (medical/health/refunds/complaints/uncertainty) → forced handoff; (2) loads structured gym knowledge via `get_gym_knowledge()`; (3) attaches member context if conversation linked; (4) detects intent (plans/trainers/location/timings/membership); (5) tries LLM provider (mock or real) with grounded system prompt; (6) falls back to canned replies using knowledge + member context. Canned fallback includes plan prices, trainer info, location, timings, membership actions. `send_outbound_reply()` logs bot replies to audit trail. Added `tests/test_p2_03_chatbot.py` (12 tests).
- Tests: backend `python -m pytest` -> 90 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 64 source files.
- Status: Done, committed.

## Iteration 40
- Task: P2-04 | Trial booking and lead capture into CRM
- Changes: Extended chatbot with trial booking intent detection (`TRIAL_KEYWORDS`) and `_handle_trial_booking()` that: extracts name/date from message, checks for existing lead/member, creates Lead with status `trial_booked` or `new`, source `whatsapp`, and optional `trial_date`. Integrated into `run_chatbot()` flow before LLM. Added `tests/test_p2_04_trial_booking.py` (6 tests).
- Tests: backend `python -m pytest` -> 97 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 64 source files.
- Status: Done, committed.

## Iteration 41
- Task: P2-05 | Human handoff and staff inbox (bot pause/resume)
- Changes: Extended chatbot with `_trigger_handoff()` that pauses conversation (`bot_paused=True`, `status=escalated`) and logs staff alert via internal messaging. Added `/whatsapp/inbox` endpoint for staff to see paused/escalated conversations with filters. Added `/whatsapp/conversations/{id}/staff-reply` for staff to reply in paused conversations (bot stays paused). Added `tests/test_p2_05_handoff.py` (6 tests).
- Tests: backend `python -m pytest` -> 103 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 64 source files.
- Status: Done, committed.

## Iteration 42
- Task: P2-06 | Guardrails, rate limits, and conversation audit
- Changes: Added `app/api/routes/whatsapp_guardrails.py` with: `GET /whatsapp/conversations/{id}/audit` for full conversation audit trail (inbound/outbound with who/what/why/template); per-number rate limiting (`check_rate_limit`, in-memory, Redis-ready); `GET/POST /whatsapp/rate-limits/{phone}` for status/reset; `GET /whatsapp/guardrails/test` for admin guardrail testing. Added `tests/test_p2_06_guardrails.py` (4 tests).
- Tests: backend `python -m pytest` -> 107 passed (exit 0). `ruff check .` exit 0, `mypy app` -> Success: no issues found in 65 source files.
- Status: Done, committed.
