# GymOS — Blockers (needs human action)

| ID | Related Task(s) | Blocker | Needed from human | Status |
|----|------------------|---------|-------------------|--------|
| BLK-001 | P1-08..P1-10, P2-* (real WhatsApp via openWA) | openWA service/session setup (unofficial WhatsApp Web automation) | Deploy/run openWA (Easy API) service, authenticate WhatsApp session (QR/link-code) on a phone number, configure webhook/event connectivity to GymOS, and review messaging policy/consent/opt-out compliance for intended use | Open (messaging mock available; see ADR 0001) |
| BLK-002 | P1-06, P1-07 (real payments via YouPI-PG) | YouPI-PG deployment and integration setup | Deploy/configure YouPI-PG instance, merchant keys/secrets/webhook endpoints, observer/bank setup as applicable, and complete legal/compliance/bank-term review; ensure idempotent reconciliation (observer/webhook events are not bank-settlement proof) | Open (payments mock + manual cash/card recording in scope; see ADR 0002) |
| BLK-004 | P2-* (real LLM for chatbot) | LLM provider API key/model choice | Provider credentials (OpenAI/Anthropic/local endpoint etc.) | Open (canned replies + human handoff fallback required) |
| BLK-005 | Production deployment | Hosting, domains, secrets management, production DB/Redis | Infra decisions and credentials | Open |

_Notes:_
- Integration targets per user direction: **openWA** for WhatsApp, **YouPI-PG** for payments; **LLM and other components remain**. See `docs/adr/0001-messaging-integration-openwa.md` and `docs/adr/0002-payments-integration-youpi-pg.md`.
- Tasks depending on real integrations must be implemented against interfaces/mocks and never claim real integration works without setup/credentials.
