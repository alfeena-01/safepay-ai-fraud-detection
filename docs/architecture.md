# Architecture

## Components

- **React + Vite** (`frontend/`): six dashboard areas for overview, transaction monitoring/details, risk analysis, account networks, investigation cases, and reports.
- **FastAPI** (`backend/app/`): REST API, request validation, CORS, and interactive OpenAPI docs.
- **SQLAlchemy 2** (`backend/app/database/`): ORM models and session lifecycle. PostgreSQL is configured with `postgresql+psycopg`; SQLite is the local/test default.
- **Risk model** (`backend/app/services/anomaly_detection_engine/` and `backend/ml/`): chunked PaySim training, calibration, held-out evaluation, and a logistic-regression scorer with per-feature log-odds explanations.

## Request/data flow

The browser calls `/api/...` through the frontend API helper. FastAPI validates JSON and query parameters, injects a database session, and reads/writes transactions, risk assessments, alerts, cases, reports, and model versions. The CSV endpoint validates and parses the upload in memory before committing any rows. No uploaded CSV or account data is written to a tracked file.

## Local ports and configuration

- Frontend: Vite default `http://localhost:5173`
- API: Uvicorn default `http://127.0.0.1:8000`
- API prefix: `/api`
- Environment: root `.env`; see `.env.example`

## Boundaries

The model uses transaction step, amount, balances, and transaction type; it excludes account identifiers and `isFlaggedFraud`. The threshold is chosen on a validation split, with final metrics measured on an untouched, natural-prevalence test split. PaySim is synthetic and row-random splits do not demonstrate production performance. Authentication/authorization and production deployment controls are not implemented. Do not expose this development service to untrusted networks or use its scores for operational decisions.