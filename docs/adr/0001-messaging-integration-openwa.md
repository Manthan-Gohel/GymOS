# ADR 0001: WhatsApp Messaging Integration via openWA

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project direction (user instruction)

## Context
GymOS requires WhatsApp messaging for templated reminders (welcome, expiry 7/3/1, payment due) and for the AI WhatsApp chatbot (inbound/outbound, handoff). Initial stack assumed WhatsApp Business Cloud API behind a provider interface with mocks for dev/tests.

User direction: "for using whatsapp api use github repo openWA" (https://github.com/open-wa/wa-automate-nodejs).

openWA (wa-automate) is a Node.js/WhatsApp Web automation toolkit (unofficial, not affiliated with WhatsApp/Meta). It can run as an Easy API service with HTTP/SSE/MCP surfaces, webhooks, and session management. It requires a WhatsApp account/session (QR/link-code auth) and operates under WhatsApp's terms and openWA's license/ToS.

## Decision
- Use **openWA** as the WhatsApp integration target for GymOS messaging/chatbot flows.
- Keep GymOS messaging behind a **provider interface** (`app.providers.messaging`) so dev/tests continue to use the mock by default (`MESSAGING_PROVIDER=mock`).
- Implement an openWA adapter in a future task that connects to a running openWA Easy API/session (HTTP) for sending messages/templates-like flows and receiving inbound webhooks/events; do not claim real operation without a configured session/service.
- Treat "approved WhatsApp templates for business-initiated messages" as a Cloud-API concept not natively guaranteed by openWA/WhatsApp Web; for openWA we must still enforce **consent, opt-out, logging (who/what/why), rate limits, and policy-compliant messaging** and record compliance considerations as blockers/risks.

## Consequences
- **Pros:** No Meta WABA app approval flow required for local/dev experimentation; flexible automation surfaces; webhook/event support.
- **Cons/Risks:** Unofficial automation (session/ban risk, ToS considerations), requires Node/openWA service and authenticated WhatsApp session, template semantics differ from Cloud API, operational reliability depends on session/phone/network.
- **Blockers:** openWA service deployment + authenticated WhatsApp session/phone number, stable webhook connectivity to GymOS, and compliance review for business messaging in target use case.
- **LLM and other components remain unchanged.**
