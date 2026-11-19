# SafePay — Financial Fraud Detection Platform

SafePay is a transaction monitoring and investigation workspace. This repository includes a FastAPI service, SQLAlchemy data model, and a React dashboard. The risk-scoring endpoint currently uses a clearly labeled demo heuristic; it is an integration placeholder, not a trained or calibrated fraud model.

## Requirements

- Python 3.11+
- Node.js 20+ and npm
- PostgreSQL 16+ for a persistent shared database (PostgreSQL 18 is also supported)
- SQLite is used by default for local development and automated tests

## Start the backend (Windows PowerShell)

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The local API is at `http://127.0.0.1:8000`; OpenAPI/Swagger documentation is at `/docs`, and health is at `/health`.

To use PostgreSQL, create a database named `safepay_db`, copy the root `.env.example` to `.env`, and set `DATABASE_URL` to your own local PostgreSQL username/password, for example:

```text
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/safepay_db
```

Never commit `.env` or put real credentials in source control. SQLAlchemy creates the tables at startup. SQLite remains the default if no database URL is configured.

## Start the frontend

In another terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). Set `VITE_API_BASE_URL` when the API is hosted somewhere other than `http://localhost:8000/api`.

## CSV dataset upload

The upload control is in **Transaction Monitoring → Upload CSV**. Use it with your PaySim CSV. The API validates the file in a streaming pass and inserts records in bounded batches; the CSV is not saved in the repository.

The API accepts a UTF-8 CSV up to 1 GB. Required columns (header matching is case-insensitive): `type`, `amount`, `nameOrig`, and `nameDest`. Standard PaySim columns are supported; `transactionId` is optional and a stable row ID is generated when it is absent. Blank amounts/balances become zero, blank account IDs become null, and blank transaction types become `UNKNOWN`. Malformed numeric values reject the whole upload. Repeated transaction IDs are skipped. The importer validates and processes the file in streaming batches rather than loading it all into memory.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

## Project documentation

- [Architecture](docs/architecture.md)
- [Database design](docs/database_design.md)
- [API documentation](docs/api_documentation.md)
- [Dataset documentation](docs/dataset_documentation.md)
- [User manual](docs/user_manual.md)
- [Testing report](docs/testing_report.md)