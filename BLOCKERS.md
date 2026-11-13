# GymOS — Blockers (needs human action)

| ID | Related Task(s) | Blocker | Needed from human | Status |
|----|------------------|---------|-------------------|--------|
| BLK-001 | P1-05.x, P2-02.x (real WhatsApp) | WhatsApp Business Cloud API credentials/app setup | Meta app, phone number ID, WABA ID, access token, approved templates | Open (mocks available) |
| BLK-002 | P1-04.x, real payments | Razorpay/UPI merchant credentials & compliance setup | Razorpay keys, webhook secret, GST/legal details for live invoices | Open (mocks available) |
| BLK-003 | P1-03.x (NFC), P3-06.x (face/NFC hardware) | NFC/biometric hardware devices & SDKs | Hardware selection, vendor SDK/docs, test devices | Open (QR software path first) |
| BLK-004 | P2-* (real LLM) | LLM provider API key/model choice | Provider credentials (OpenAI/Anthropic/local endpoint etc.) | Open (rule-based fallback + mock interface) |
| BLK-005 | Production deployment | Hosting, domains, secrets management, production DB/Redis | Infra decisions and credentials | Open |

_Note: Tasks depending on real integrations must be implemented against interfaces/mocks and marked appropriately; never claim real integration works without credentials/hardware._
