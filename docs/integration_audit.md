# SafePay Integration Audit

## Source archives inspected
- `SafePay.zip`: existing FastAPI backend, React/Vite frontend, SQLAlchemy data model, CSV importer, model artefacts and documentation.
- `SafePay_AI_Chatbot(1).zip`: standalone chatbot backend and React widget. Its original demo page used hard-coded preview transaction details and its README noted it was not connected to the SafePay database. The demo data was not carried into the live application.

## Integrated application
- Kept the existing FastAPI + SQLAlchemy + React/Vite architecture and existing dashboard, transaction, risk, case, alert and report features.
- Integrated the chatbot widget into the existing React app and mounted its API router in the existing FastAPI process. No separate chatbot server is needed.
- Chat requests containing `TX...` or `TXN...` identifiers resolve those identifiers against the live SafePay database. The assistant is supplied stored transaction details, any stored assessment and account links. Unknown IDs receive an explicit not-found answer.
- Chatbot defaults to deterministic safe fallback responses (`CHATBOT_PROVIDER=rules`). Optional Ollama uses `CHATBOT_PROVIDER=ollama`; if unavailable, safe fallback remains available.
- Added secure sign-in/analyst registration, PBKDF2-HMAC-SHA256 password hashing, signed expiring bearer tokens, sessionStorage token handling, and an authenticated `/api/auth/me` endpoint.
- Added role gates: dataset upload and model analysis are restricted to `admin` and `analyst`; self-registration creates analyst accounts. A first admin can be bootstrapped using `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables before startup.
- Expanded account network API to depth 1–3 (multi-hop) with capped traversal, transaction edge metadata, depth labels and a warning that graph links are not proof of coordinated fraud.
- Added CI workflow, team ownership guidance, PR/branch rules, environment template updates and test reports.

## Existing modules retained
- FastAPI APIs for dashboard, dataset upload/summary, transactions, predictions, alerts, account network, cases and reports.
- SQLAlchemy entities for transactions, risk assessments, alerts, cases, reports and model versions; added a users table without deleting existing models.
- Existing ML, anomaly detection, graph-intelligence and investigation service modules, saved model files, tests and sample data.

## Verification performed
- Backend automated suite: **44 passed**.
- Python backend syntax compilation: passed.
- Frontend JSX/JavaScript syntax transpilation check: passed for `App.jsx`, `SafePayChatbot.jsx`, `main.jsx` and `api.js`.
- Frontend production bundle: **not verified**. `npm ci` could not complete in this environment (online install timed out and offline cache lacked a package); run `npm ci` and `npm run build` on the development machine.
- PostgreSQL deployment and real browser end-to-end tests were not run.

## Remaining risks / not represented as complete
- This is not production banking software. No regulatory/security certification, penetration test, rate limiting, audit-grade immutable event log, account lockout, MFA, refresh-token rotation or server-side token revocation is included.
- Tokens are signed bearer tokens with expiry. Signing secret must be unique and protected; HTTPS is required outside localhost. Logout clears the browser session token; it does not revoke an already issued token server-side.
- Registration is open and creates analyst accounts. Protect public deployments with an invitation/approval process before allowing signups.
- Investigator role is restricted from data upload and model execution; broader case/report permissions should be reviewed against the team's actual operational policy.
- Graph traversal is bounded and returns account relationships, not a formal proof of collusion. It is not a full community-detection or money-mule-ring classifier.
- The ML model documentation describes an educational PaySim-trained model. Scores and labels require human review and must not be used for automated account blocking or real-world accusations.
- Database schema is created with SQLAlchemy `create_all`; a formal Alembic migration workflow is still recommended before shared production-like deployments.
