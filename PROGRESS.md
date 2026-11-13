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

