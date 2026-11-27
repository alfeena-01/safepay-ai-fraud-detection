# Testing report

## Automated verification in the integration workspace

- **44 backend tests passed** using `PYTHONPATH=backend python -m pytest -q backend/tests`.
- Python syntax compilation passed for `backend/app`.
- JSX/JavaScript syntax transpilation passed for the main React app, chatbot component, frontend entry point and API client.
- Backend API tests cover CSV ingestion/validation, duplicate handling, transaction search, risk analysis, alert creation, case/report workflows, dashboard metrics, depth-2 account traversal, authentication, password hashing, token signature checks and role restrictions.
- Chatbot tests cover safe context handling and missing/available transaction details.

## Frontend production build

Not verified in this environment. Online `npm ci` timed out and offline installation could not retrieve an uncached dependency. On the Windows development machine run:

```powershell
cd frontend
npm ci
npm run build
```

## Not run / still required

- PostgreSQL connectivity and shared-team database validation.
- Browser-based end-to-end testing across login, upload, model analysis, graph, chatbot, cases and reports.
- Production security review, penetration testing, rate limiting, MFA and token revocation.
- Ollama-backed chatbot test (the rules-based safe fallback is the default).

Use synthetic or authorised test data. The supplied PaySim model is educational and its outputs are decision-support signals, not proof of fraud.
