# GymOS — Blockers (needs human action)

| ID | Related Task(s) | Blocker | Needed from human | Status |
|----|------------------|---------|-------------------|--------|
| BLK-001 | P1-08..P1-10, P2-* (real WhatsApp) | WhatsApp Business Cloud API credentials/app setup | Meta app, phone number ID, WABA ID, access token, approved templates for business-initiated messages | Open (mocks available) |
| BLK-002 | P1-06, P1-07 (real payments) | Razorpay/UPI merchant credentials & compliance setup | Razorpay keys, webhook secret, GST/legal details for live invoices | Open (mocks available) |
| BLK-004 | P2-* (real LLM for chatbot) | LLM provider API key/model choice | Provider credentials (OpenAI/Anthropic/local endpoint etc.) | Open (canned replies + human handoff fallback required) |
| BLK-005 | Production deployment | Hosting, domains, secrets management, production DB/Redis | Infra decisions and credentials | Open |

_Notes:_
- OUT-of-scope items removed per scope pivot (NFC/biometric hardware no longer tracked; previous BLK-003 dropped).
- Tasks depending on real integrations must be implemented against interfaces/mocks and marked "needs credentials" in docs/BLOCKERS; never claim real integration works without credentials.
