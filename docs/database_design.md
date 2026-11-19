# Database design

SQLAlchemy creates the schema on API startup. PostgreSQL is the intended shared database; SQLite is the zero-setup development/test default. All primary keys are integer IDs, with a unique source transaction ID for idempotent imports.

| Table | Purpose | Important relationships |
|---|---|---|
| `transactions` | PaySim-style transaction facts and optional labels | One-to-one risk assessment; one-to-many alerts |
| `risk_assessments` | Demo/model fraud, anomaly, graph, and overall scores | Unique FK to `transactions` |
| `alerts` | Review queue and workflow state | FK to `transactions` |
| `investigation_cases` | Case owner, status, priority, description, notes | Optional FK to `transactions` |
| `investigation_reports` | Generated report title/content | Optional FKs to case and transaction |
| `model_versions` | Model name, version, and JSON metrics | Independent model metadata |

Indexes cover transaction IDs, types, account IDs, steps, fraud labels, risk levels, case/alert state, and foreign keys. Foreign keys use cascade when a transaction is deleted for its risk/alert records and `SET NULL` for historical case/report references.

## PostgreSQL setup

Create `safepay_db` in pgAdmin or with `CREATE DATABASE safepay_db;`, then set the private `DATABASE_URL` in the root `.env`. The application uses parameterized SQLAlchemy statements; no credentials are stored in models or committed files.