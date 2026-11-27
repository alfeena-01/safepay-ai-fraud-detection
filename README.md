# SafePay — Financial Fraud Detection Platform

SafePay is a transaction monitoring and investigation workspace. This repository includes a FastAPI service, SQLAlchemy data model, and a React dashboard. Transaction risk analysis uses an explainable logistic model trained and evaluated on synthetic PaySim data; its results are not production validated.

## Requirements

- Python 3.11+
- Node.js 20+ and npm
- PostgreSQL 16+ for a persistent shared database (PostgreSQL 18 is also supported)
- SQLite is used by default for local development and automated tests

## Start the backend (Windows PowerShell)

From the repository root, first create your local environment file and a unique signing secret:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `.env` as `SECRET_KEY`. For a first administrator account, set `ADMIN_EMAIL` and a strong `ADMIN_PASSWORD` (10–128 characters) in `.env` before the first backend start. If you do not configure an administrator, users can self-register as `analyst`; do not grant admin privileges by editing client-side data.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The local API is at `http://127.0.0.1:8000`; OpenAPI/Swagger documentation is at `/docs`, and health is at `/health`. All application APIs require a signed bearer access token. The frontend provides sign-in and analyst registration. The backend stores password hashes (PBKDF2-HMAC-SHA256), never plaintext passwords. Admins and analysts can upload datasets and run model analysis; investigator accounts are read/investigation users. Tokens expire after the configured `ACCESS_TOKEN_TTL_SECONDS` (default eight hours).

### Train the risk model

Before running transaction analysis, train the explainable logistic-regression model with a labeled PaySim CSV. From the `backend` directory, run:

```powershell
.\.venv\Scripts\python.exe -m ml.train_explainable --dataset "C:\path\to\PS_20174392719_1491204439457_log.csv"
```

Training reads the CSV in chunks, uses `isFraud` as the label, samples only the training negatives, and preserves natural class prevalence in separate calibration, validation, and test splits. It saves the model under `backend/ml/saved_models/` and held-out metrics in `evaluation.json`. The account IDs and `isFlaggedFraud` field are excluded from model features. The risk page shows the top model-feature contributions for each assessment.

The provided PaySim data is synthetic. Its held-out metrics are educational evaluation, not evidence that the model is suitable for real-world fraud decisions. Do not expose this development service to untrusted networks or rely on its scores for operational decisions.

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

The API accepts a UTF-8 CSV up to 1 GB. Required columns (header matching is case-insensitive): `type`, `amount`, `nameOrig`, and `nameDest`. Standard PaySim columns are supported; `transactionId` is optional and a stable row ID is generated when it is absent. `isFraud` is optional: recognized `1`/`true`/`yes` and `0`/`false`/`no` values are recorded as known ground-truth labels; a blank or absent value remains unknown and is never counted as legitimate. Other nonblank label values reject the upload. Blank amounts/balances become zero, blank account IDs become null, and blank transaction types become `UNKNOWN`. Malformed numeric values reject the whole upload. Repeated transaction IDs are skipped. The importer validates and processes the file in streaming batches rather than loading it all into memory.

For individual records or external payment-system integrations, use the protected JSON endpoints documented in `/docs`: `POST /api/transactions/ingest` accepts one transaction and `POST /api/transactions/ingest/batch` accepts up to 500. Both require an analyst/admin bearer token from `/api/auth/login` and skip duplicate transaction IDs. `GET /api/transactions/live` lists externally ingested and simulated events separately from CSV history.

To generate clearly labeled local demo traffic, call `POST /api/transactions/simulator/start` with `{"interval_seconds": 2, "scenario": "mixed"}`; available scenarios are `normal`, `suspicious`, and `mixed`. Stop it with `POST /api/transactions/simulator/stop` and check `GET /api/transactions/simulator/status`. These records are synthetic examples, not real bank/UPI events or ground-truth fraud labels. New events receive the active supervised model assessment automatically. Independent Isolation Forest assessment is marked unavailable until there are at least 50 earlier historical CSV records; sender behavior similarly requires five prior outgoing records.

After uploading a historical CSV, use **Risk Analysis → Analyze pending CSV records** to assess up to 100 previously unassessed rows (up to 500 via the API). The transaction table presents known ground-truth labels separately from model estimates; the risk page presents a model classification using the trained artifact's configured decision threshold, alongside the calibrated probability. CSV `isFraud` labels are ground truth; model predictions are separate estimates. Unknown ground-truth labels remain distinct from legitimate labels throughout the dashboard and reports.

Every high-risk assessment creates one open alert per transaction for analyst review. This applies to newly ingested events, simulator traffic, individual analysis, and historical CSV batch analysis. The dashboard refreshes its metrics, latest live events, and alerts every five seconds; alerts can be acknowledged and resolved from the dashboard.

Transaction records are currently accepted as structured UTF-8 CSV or JSON. Arbitrary office documents, PDFs, or binary files are not treated as transaction data.

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
- [Four-member integration contracts](docs/TEAM_INTEGRATION_CONTRACTS.md)
- [Contribution guidelines](CONTRIBUTING.md)
- [GitHub update guide](GITHUB_UPDATE_GUIDE.md)
- [Testing report](docs/testing_report.md)

## Integrated chatbot

The SafePay Assistant is now mounted in the main React application and served by the existing FastAPI backend. It uses the same database. Ask about a specific transaction by including its transaction ID (for example, `Explain TXN123`). The API looks up the ID in the database and supplies the stored transaction and risk assessment to the assistant. It does not invent missing records.

By default, `CHATBOT_PROVIDER=rules` uses the built-in safe response engine and needs no local LLM. To optionally use Ollama, add `CHATBOT_PROVIDER=ollama`, `OLLAMA_URL=http://localhost:11434/api/chat`, and `OLLAMA_MODEL=llama3.2` to `backend/.env`. Install and run Ollama separately. If it is unavailable, the API falls back to safe local responses.

See [Integration audit](docs/integration_audit.md) for implemented scope and outstanding gaps. This is still a hackathon/educational decision-support prototype, not a regulated banking service. Use synthetic or authorised test data, deploy only behind HTTPS and a trusted network boundary, and complete the remaining production-security review before handling sensitive financial data.


## Integrated team modules

See [docs/INTEGRATED_MODULES.md](docs/INTEGRATED_MODULES.md) for the merged Member 3 endpoint, SafePay1 source modules, and chatbot integration notes.
