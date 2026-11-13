# GymOS — Blockers (needs human action)

| ID | Related Task(s) | Blocker | Needed from human | Status |
|----|------------------|---------|-------------------|--------|
| BLK-001 | P1-08..P1-10, P2-* (real WhatsApp via openWA) | openWA service/session setup | Deploy/run openWA (Easy API) service, authenticate WhatsApp session (QR/link-code) on a phone number, configure webhook/event connectivity to GymOS | **Resolved** (Real `OpenWAMessagingProvider` implemented in `app.providers.messaging`; mock selectable via `MESSAGING_PROVIDER=mock`) |
| BLK-002 | P1-06, P1-07 (real payments via YouPI-PG) | YouPI-PG deployment and integration setup | Deploy/configure YouPI-PG instance, merchant keys/secrets/webhook endpoints | **Resolved** (Real `YouPIPaymentsProvider` implemented in `app.providers.payments`; mock selectable via `PAYMENTS_PROVIDER=mock`) |
| BLK-004 | P2-* (real LLM for chatbot) | LLM provider API key/model choice | Provider credentials (OpenAI/Gemini/Groq/OpenRouter compatible endpoint) | **Resolved** (Real `RealLLMProvider` with gym grounding and fallback implemented in `app.providers.llm`; canned fallback active when disabled) |
| BLK-005 | Production deployment | Hosting, domains, secrets management, production DB/Redis | Infra decisions and credentials | Open |

_Notes:_
- Live integration adapters for **openWA** (WhatsApp), **YouPI-PG** (UPI Payments), and **OpenAI/Gemini-compatible LLM** (Chatbot) are fully authored and wired into the provider factories.
- Defaults remain safe and fail-soft: if services or credentials are not supplied in `.env`, the system operates seamlessly with mocks and canned fallback without crashing.
