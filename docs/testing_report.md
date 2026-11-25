# Testing report

## Automated coverage

`backend/tests/test_api.py` exercises CSV ingestion and duplicate handling, transaction search, risk analysis and alert creation, case creation/notes/status updates, report generation, dashboard metrics, account network data, malformed CSV headers, and invalid case requests.

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

SQLite in-memory databases are used for isolated API tests; the same SQLAlchemy models are used with PostgreSQL when configured.

Latest local validation: **4 backend tests passed** and `npm run build` completed successfully. The running SQLite-backed API returned a healthy status and dashboard metrics, and the Vite page loaded successfully. npm audit reported no known package vulnerabilities.

## Manual checks still needed

- Connect to the local PostgreSQL 18 service after the developer sets a private `DATABASE_URL`; service availability was confirmed, but no database credentials were available to test a PostgreSQL connection.
- Upload and inspect the project owner's real CSV; this is intentionally pending so the file is not guessed or fabricated.
- Confirm results in the browser after the frontend is built and the API is running.
- Test database-unavailable behavior and the final full workflow in the target environment.