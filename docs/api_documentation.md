# API documentation

Base URL: `http://127.0.0.1:8000`; routes below are prefixed with `/api`. Interactive request/response schemas are available at `/docs`.

| Method | Route | Purpose |
|---|---|---|
| GET | `/dashboard/metrics` | Dashboard cards, activity series, risk distribution |
| POST | `/dataset/upload` | Validate and import a multipart CSV (`file`) |
| GET | `/dataset/summary` | Row count, fraud-label count/rate, amount sum |
| GET | `/transactions/` | Paginated list; optional `q`, `transaction_type`, `risk_level`, `fraud_only`, `offset`, `limit` |
| GET | `/transactions/{id}` | Transaction detail and any risk result |
| POST | `/transactions/{id}/analyze` | Run demo heuristic and persist result/possible alert |
| GET | `/predictions/{transaction_id}` | Retrieve a saved risk result by source transaction ID |
| GET | `/alerts/` | Alert queue; optional `status` |
| PATCH | `/alerts/{alert_id}?status=` | Set `open`, `acknowledged`, or `resolved` |
| GET | `/accounts/{account_id}/network` | Up to 200 account-linked transactions, nodes, and flagged connections |
| GET | `/cases/` | Case list; optional status |
| POST | `/cases/` | Create case |
| PATCH | `/cases/{case_id}` | Update case metadata/status |
| POST | `/cases/{case_id}/notes` | Append a validated investigation note |
| GET | `/reports/` | List reports |
| POST | `/reports/` | Create a report; generates a summary if content is omitted |
| GET | `/reports/{report_id}` | Report detail |

JSON errors use FastAPI's standard `detail` shape. Upload validation returns 4xx responses for unsupported files, oversized content, missing required headers, and malformed numeric values. List endpoints are bounded; transaction `limit` cannot exceed 100.