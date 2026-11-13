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

