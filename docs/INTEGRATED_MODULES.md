# SafePay Integrated Modules

## Main application
`backend/app/main.py` remains the single FastAPI entry point and the existing React dashboard remains the main frontend.
The existing SafePay chatbot is already present in `frontend/src/components/SafePayChatbot.jsx` and its main API is
`POST /api/chat` (with transaction context lookup in the SafePay database).

## Member 3
Member 3's detector source is preserved under `backend/app/extensions/member3/app/detectors/`.
A unified adapter is registered at `POST /api/member3/assess`. It runs phishing URL, account takeover,
suspicious login, duplicate transaction, fraud pattern and device fingerprint checks, then calculates the
weighted Member 3 risk score. It is protected by the main application's existing authentication middleware.
Input history and known-device values must come from a trusted application data source in a real deployment;
empty defaults are demo-only.

Example request body:
```json
{
  "transaction_id": "TXN-DEMO-01",
  "account_id": "ACC-DEMO-01",
  "amount": 1200,
  "merchant": "Demo Store",
  "timestamp": "2026-11-26 14:00",
  "url": "https://example.com",
  "failed_login_attempts": 0,
  "password_reset_attempts": 0,
  "new_device": true,
  "unusual_time": false,
  "unusual_location": false,
  "profile_changed": false,
  "device": {
    "device_type": "Mobile",
    "os": "Android",
    "browser": "Chrome",
    "screen_resolution": "1080x2400"
  },
  "previous_transactions": [],
  "known_devices": []
}
```

## SafePay1
SafePay1 backend source is preserved under `backend/extensions/safepay1_source/` so its fraud, emergency,
history, language, voice and transaction-ML work is retained without replacing the original SafePay API.
These files are kept namespaced because they were written as a second standalone FastAPI app and use overlapping
`app.*` module paths. They are not silently mounted as duplicate live endpoints. The main SafePay platform
already provides transaction ingestion, ML risk analysis, alerts, investigation and reporting. Review/adapt
individual SafePay1 features before exposing them in the main API.

The 470 MB SafePay1 raw CSV was not duplicated. The original SafePay project already contains its PaySim
dataset and supports uploading a CSV through Transaction Monitoring.

## Chatbot
The supplied chatbot's backend source and `.env.example` are retained under
`backend/extensions/chatbot_reference/` for reference. Do not start it as a second server on port 8000.
Use the main SafePay `/api/chat` endpoint and the existing React chatbot component to avoid duplicate chat services.
Ollama is optional; configure `CHATBOT_PROVIDER=ollama` and install/run the model only if desired.

## Important integration notes
- Existing original SafePay files are the base and were not intentionally replaced by SafePay1.
- Generated `__pycache__`, Python bytecode, virtual environments and `node_modules` were excluded; reinstall dependencies locally.
- Do not use the demo rule-based scores as proof of fraud or as an automatic account-blocking decision.
- Run the backend tests and manually test `/health`, login, dashboard, `/api/chat`, and `/api/member3/assess`.
