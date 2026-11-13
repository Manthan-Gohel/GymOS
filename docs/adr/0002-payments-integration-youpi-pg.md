# ADR 0002: Payments Integration via YouPI-PG

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Project direction (user instruction)

## Context
GymOS requires payment recording (cash/UPI/card), dues, receipts/GST-ready invoices, and later reconciliation flows. Initial stack assumed Razorpay/UPI behind a provider interface with mocks for dev/tests.

User direction: "for payment https://github.com/youpi-pg/YouPI-PG" (LLM and other remain).

YouPI-PG is a self-hosted UPI payment gateway/research project (Node.js, observer-based bank alert verification, direct-to-bank settlement model) with its own checkout/merchant/admin components and explicit experimental/compliance warnings. It is not a drop-in API equivalent to Razorpay and carries operational/legal/reliability considerations per its documentation.

## Decision
- Use **YouPI-PG** as the target payment integration for UPI/gateway flows in GymOS.
- Keep GymOS payments behind a **provider interface** (`app.providers.payments`) with mock as default for dev/tests (`PAYMENTS_PROVIDER=mock`).
- Integrate via YouPI-PG's supported integration surfaces (embed/checkout + signed server-to-server webhooks/events) in future tasks; treat observer-based statuses and webhooks as **not bank-settlement proof** and require reconciliation/validation per GymOS rules.
- Cash/card manual recording remains a first-class GymOS capability (staff-entered) independent of gateway integration.
- Do not claim real payment processing works without a deployed/configured YouPI-PG instance, merchant setup, observers, and credentials/secrets.

## Consequences
- **Pros:** Aligns with direct-to-bank/self-hosted direction requested by user.
- **Cons/Risks:** YouPI-PG is experimental/research-oriented with stated limits and risks (alert parsing/attribution, compliance, operational burden); integration complexity higher than a standard PSP SDK; requires careful reconciliation and idempotent webhook handling.
- **Blockers:** YouPI-PG deployment/configuration, merchant keys/secrets/webhook endpoints, observer setup (as applicable), and legal/compliance/bank-term review for intended use.
- **LLM and other components remain unchanged.**
