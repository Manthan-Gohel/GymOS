# GymOS — Decisions & Assumptions

| Date | Iteration | Decision | Rationale | Alternatives considered |
|------|-----------|----------|-----------|-------------------------|
| 2026-11-13 | 0 | Project root at `C:\Users\manth\GymOS` | Clean dedicated workspace inside user home; avoids cluttering home dir | Use existing folder; rejected for clarity |
| 2026-11-13 | 0 | Start with monorepo-style layout (`backend/`, `frontend/`, `infra/`, shared docs) | Simplifies coordination, CI, and Docker Compose for MVP | Separate repos; overkill now |
| 2026-11-13 | 0 | Celery + Redis as default job scheduler choice (can ADR later if ARQ preferred) | Mature, well-known for scheduled reminders/automations | ARQ; simpler but less common for complex schedules |
| 2026-11-13 | 0 | Use SQLite for fast local unit tests where possible, Postgres in Docker/CI integration | Speed for TDD loop while keeping Postgres compatibility | Postgres-only; slower baseline runs |
| 2026-11-13 | 0 | All external integrations behind interfaces with mock implementations default in dev/test | Satisfies "mocks for dev/tests, never fake real integrations" rule | Direct SDK usage; unsafe without creds |
| 2026-11-13 | 4 | Scope pivot to owner/staff-only GymOS (no member-facing surfaces, WhatsApp chatbot as only AI) | User directive with hard OUT boundaries; prevents building QR/NFC/member attendance, member app/PWA/login, AI Gym Manager, automated lead follow-up sequences, workout/diet AI, progress tracking, inactive-member/retention/renewal AI, occupancy analytics, forecasting, AI business recommendations, face check-in, predictive maintenance | Keep previous broader scope; rejected per explicit instruction |
| 2026-11-13 | 4 | Dropped OUT backlog items/tasks from previous plan (member PWA P1-22, QR/check-in/shared-detection P1-06..P1-08, member role in RBAC, broad Phase 2 AI suite P2-01..P2-10 old, advanced analytics/forecasting/face/occupancy P3-02/04/05/06 old, etc.) and rewrote PLAN/BACKLOG | Align with IN/OUT scope; removed member role from auth/RBAC target; kept only chatbot AI in Phase 2 and multi-branch owner dashboard+permissions in Phase 3 | Partially retain; would violate scope |
| 2026-11-13 | 4 | Kept completed P0-01..P0-03 as-is (scaffold/bootstrap/compose) | Still valid foundation under new scope | Revert; unnecessary rework |

| 2026-11-13 | 16 | Messaging integration target changed to **openWA** (https://github.com/open-wa/wa-automate-nodejs) instead of WhatsApp Business Cloud API; keep provider interface + mock default | User direction; openWA provides WhatsApp Web automation/Easy API/webhooks but is unofficial and requires session/phone; ADR 0001 documents trade-offs and compliance/operational risks | Continue with Cloud API; rejected per user |
| 2026-11-13 | 16 | Payments integration target changed to **YouPI-PG** (https://github.com/youpi-pg/YouPI-PG) instead of Razorpay/UPI PSP; keep provider interface + mock default, cash/card manual recording remains in GymOS | User direction; YouPI-PG is self-hosted/experimental UPI gateway requiring careful webhook reconciliation and ops; ADR 0002 documents risks | Razorpay/UPI SDK; rejected per user |
| 2026-11-13 | 16 | LLM and other components remain as-is (provider-agnostic, chatbot-only, fallback to canned replies + handoff) | Explicit user instruction "llm and other will remain" | Replace LLM stack; rejected |

_Assumptions will be recorded here as they arise. Significant architectural changes require ADR in /docs/adr/._
