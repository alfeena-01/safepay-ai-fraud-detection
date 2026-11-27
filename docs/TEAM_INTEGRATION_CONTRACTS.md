# Four-member integration contracts

The team works in one repository and one application. Each member owns a module boundary; shared interfaces are reviewed before merging.

| Owner | Main folders | Deliverables | Shared contract |
|---|---|---|---|
| Member 1 — Frontend/UI | `frontend/src/App.jsx`, `frontend/src/components/`, `frontend/src/styles.css` | Dashboard, transaction views, responsive pages, charts, network visualization | Call the documented API through `frontend/src/services/api.js`; do not embed fake results as live data |
| Member 2 — Backend/DB | `backend/app/api/`, `backend/app/database/`, `backend/app/core/` | FastAPI routes, SQLAlchemy models, auth, data validation, DB config | Keep response schemas stable; coordinate model/schema migrations before merge |
| Member 3 — AI/ML | `backend/app/services/anomaly_detection_engine/`, `backend/app/services/transaction_ml_engine/`, `backend/ml/` | Training, validation, inference, calibrated risk estimates, feature explanations | Return the risk assessment contract used by `RiskAssessment`; include model version and explicit limitations |
| Member 4 — Investigation | `backend/app/services/graph_intelligence_engine/`, `backend/app/api/graph.py`, `backend/app/api/cases.py`, `backend/app/api/reports.py`, `backend/app/api/chat.py`, chatbot component | Multi-hop account exploration, investigation workflow, report generation, database-grounded assistant | Use transaction IDs and persisted assessment records; graph links and AI scores are signals, not proof |

## API contracts

- Authentication: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`. Protected routes require `Authorization: Bearer <token>`.
- Transaction read: `GET /api/transactions/?q=&risk_level=&offset=&limit=`.
- Model analysis: `POST /api/transactions/{database_id}/analyze`; response is a persisted `RiskRead`.
- Account graph: `GET /api/accounts/{account_id}/network?depth=1|2|3`; returns `connected_accounts`, directed `edges`, `depth`, `truncated`, and a non-accusatory disclaimer.
- Chatbot: `POST /api/chat` with `message`, optional `history`; transaction identifiers are resolved server-side. Never pass arbitrary browser-generated transaction facts as authoritative data.
- Cases and reports: `/api/cases/` and `/api/reports/`; database IDs are numeric foreign keys, while external transaction identifiers are strings.

## Merge rules

1. Branch from `develop`; do not work directly on `main`.
2. Use one feature branch per owner and keep commits focused.
3. For changes to `main.py`, SQLAlchemy models, Pydantic schemas, API response contracts, `App.jsx`, requirements, or package lock, request a second member's review.
4. CI must pass backend tests and frontend production build before merge.
5. Merge feature PRs into `develop`; create a reviewed release PR from `develop` to `main`.
6. Never force-push shared branches, commit secrets, or include raw customer financial records.
