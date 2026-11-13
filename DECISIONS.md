# GymOS — Decisions & Assumptions

| Date | Iteration | Decision | Rationale | Alternatives considered |
|------|-----------|----------|-----------|-------------------------|
| 2026-11-13 | 0 | Project root at `C:\Users\manth\GymOS` | Clean dedicated workspace inside user home; avoids cluttering home dir | Use existing folder; rejected for clarity |
| 2026-11-13 | 0 | Start with monorepo-style layout (`backend/`, `frontend/`, `infra/`, shared docs) | Simplifies coordination, CI, and Docker Compose for MVP | Separate repos; overkill now |
| 2026-11-13 | 0 | Celery + Redis as default job scheduler choice (can ADR later if ARQ preferred) | Mature, well-known for scheduled reminders/automations | ARQ; simpler but less common for complex schedules |
| 2026-11-13 | 0 | Use SQLite for fast local unit tests where possible, Postgres in Docker/CI integration | Speed for TDD loop while keeping Postgres compatibility | Postgres-only; slower baseline runs |
| 2026-11-13 | 0 | All external integrations behind interfaces with mock implementations default in dev/test | Satisfies "mocks for dev/tests, never fake real integrations" rule | Direct SDK usage; unsafe without creds |

_Assumptions will be recorded here as they arise. Significant architectural changes require ADR in /docs/adr/._
