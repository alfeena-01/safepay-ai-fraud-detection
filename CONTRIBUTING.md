# Contributing to SafePay

## Team ownership

- Member 1 — React UI/UX, dashboard, transaction pages, charts and responsive styling.
- Member 2 — FastAPI endpoints, SQLAlchemy models, database configuration, authentication and API security, CSV/data APIs.
- Member 3 — model training, preprocessing, anomaly detection, prediction scoring and explainability.
- Member 4 — graph investigation, multi-hop account analysis, case/report workflows, chatbot and investigation experience.

Agree on API contracts before changing shared models or response schemas. Keep feature work inside the owning module where possible.

## Branch strategy

- `main`: reviewed, demo-ready baseline only.
- `develop`: integration branch.
- `feature/frontend`, `feature/backend`, `feature/ai-fraud-detection`, `feature/investigation-chatbot`: suggested feature branches.

Create a feature branch from `develop`, commit focused changes, push the branch, and open a pull request into `develop`. Require another member to review changes to shared files (`backend/app/main.py`, database models/schemas, frontend `App.jsx`, dependency files). Merge `develop` into `main` only after the test checklist passes. Do not force-push shared branches or commit directly to `main`.

## Local checks

Backend:

```powershell
cd backend
python -m pytest -q
```

Frontend:

```powershell
cd frontend
npm ci
npm run build
```

Do not commit `.env`, virtual environments, `node_modules`, local database files, raw private datasets, or generated secrets. Use synthetic datasets for tests and demos.
