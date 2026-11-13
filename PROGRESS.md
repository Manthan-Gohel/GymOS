# GymOS — Progress Log

> Iteration history for phases 0–2 was reconstructed from git history after an
> accidental overwrite; commit hashes are the source of truth.

## Phase 0: Foundation (P0-01..P0-15) — done
- Scaffold, FastAPI bootstrap, docker-compose, CI, ruff+mypy baseline.
- Multi-tenant core schema (all tables carry gym_id/branch_id) + Alembic migrations.
- Tenant scoping primitives, JWT auth (owner/admin/reception/trainer), RBAC, audit log.
- Provider interfaces: messaging (openWA), payments (YouPI-PG), LLM — each with mock + fallback.
- Celery/Redis scheduler for reminders. Commits 81be159..75d77d5.

## Phase 1: Owner/staff operations MVP (P1-01..P1-23) — done
- Member records + audit; plans; membership lifecycle (purchase/freeze/upgrade/expiry).
- GST-ready invoices, payments/dues/late fees, receipts.
- WhatsApp templates + opt-out, outbound message audit, automated reminders.
- Trainers/availability/assignments, session booking, trainer attendance.
- Staff attendance/payroll, expenses, daily dashboard API.
- CRM leads, complaints, equipment + maintenance.
- React+Vite+TS+Tailwind frontend; reception/admin/owner/trainer panels wired to APIs.
- Commits 031ff14..e253753.

## Phase 2: AI WhatsApp chatbot (P2-01..P2-08) — done
- Inbound webhook + conversation store; grounded gym knowledge source.
- FAQ chatbot (LLM interface, strict grounding, canned fallback + human handoff).
- Trial booking → CRM leads; staff inbox (bot pause/resume + staff replies).
- Guardrails (medical/refund/complaint keywords), per-number rate limits, audit.
- 17-case eval set (tests/eval_chatbot.py).
- Commits 2f64a23..2f8d35f; live providers for openWA/YouPI-PG/LLM in 89deaaf.

## Phase 3: Multi-branch (P3-01..P3-03) — done
- P3-01/P3-02: branch-filtered `/dashboard/daily`, `/dashboard/summary`,
  `/dashboard/branch-comparison` in `finance.py`; `check_branch_access()` in
  `core/rbac.py`; owners (branch_id=None) see all branches, staff auto-scoped.
- Tests: `tests/test_p3_01_branch_dashboard.py`.
- Release readiness documented; full suite green.

## Iteration 48 — Mode: Ponytail Full
- Lazy senior dev mode active: YAGNI → stdlib → native → existing dep → one line.
- Deliberate simplifications marked with `ponytail:` comments.

## Iteration 49 — Security hardening (VULN-001..VULN-009)
- **VULN-001** Insecure default JWT secret: `field_validator` on `secret_key`
  rejects default/short secrets when `app_env ∈ {production, staging}`.
- **VULN-002** Unauthenticated webhook + tenant spoofing: HMAC-SHA256 over raw
  body (`X-GymOS-Signature`) + new per-gym `webhook_token` column;
  production route `POST /whatsapp/webhook/{gym_token}` resolves the tenant from
  the URL token — `payload.gym_id` is ignored; legacy `/whatsapp/webhook` is
  403 in production/staging. Migration `f1a2c3d4e5f6`.
- **VULN-003** Invoice cross-tenant IDOR: `create_invoice` validates member/
  membership/payment refs belong to caller's gym before generating.
- **VULN-004** KYC/health PII exposure: `kyc_id_number` masked (`****`+last4) for
  all roles except owner/admin; `health_notes` hidden from trainer, kept for
  reception (front desk) and owner/admin.
- **VULN-005** Login rate limiting + user-enumeration timing: per
  `ip:gym_id:email` sliding window (10/min default) and dummy bcrypt hash for
  unknown emails so response timing is uniform.
- **VULN-006** In-memory rate limiter under multiple workers: new
  `services/ratelimit.py` with Redis sliding window (zset) and process-local
  fallback on Redis failure (`ponytail:` simplification documented).
- **VULN-007** Missing CORS: `CORSMiddleware` registered from explicit origin
  allow-list; no wildcard origins.
- **VULN-008** JWT in localStorage: auth sets HttpOnly/SameSite=lax cookie
  (`Secure` when `cookie_secure=true`) and returns token in body; `get_current_user`
  falls back to cookie; frontend keeps token in memory only, uses
  `credentials: 'include'`, restores session via `/auth/me`, and calls
  `POST /auth/logout`.
- **VULN-009** Exposed DB/Redis ports + default creds: compose binds removed
  (internal `expose` only), `POSTGRES_PASSWORD` now required (`:?`), DATABASE_URL
  defaults wire the same secret.
- Local LLM: `ollama` recognized in `get_llm_provider()`; `RealLLMProvider` omits
  Authorization when no key (Ollama needs none); defaults point at
  `http://localhost:11434/v1` + `llama3.1`; canned fallback + handoff preserved on
  error. `backend/.env.example` added.
- Tests added: `test_sec02_webhook_token.py` (5), `test_sec04_pii_masking.py` (3),
  `test_sec05_ollama_llm.py` (4); dashboard unauth test now clears the auth cookie
  first (cookie fallback makes bare-header 401 checks invalid).
- Status: **135 tests passing**, ruff clean, mypy clean (66 files), frontend build OK.

## Deferred (explicitly out of scope)
- BLK-001/002/004 real deployments (openWA, YouPI-PG, hosted LLM keys) — live
  providers are implemented and unit-tested, real endpoints not exercised.
- Production hosting/release (BLK-005) — blocked until infra is provisioned.
- Playwright E2E re-run pending after VULN-008 frontend auth change.
