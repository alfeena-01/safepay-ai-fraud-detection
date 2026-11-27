# API documentation

Base URL: `http://127.0.0.1:8000`; routes below are prefixed with `/api`. Except registration/login, send `Authorization: Bearer <access_token>` with API requests. Interactive request/response schemas are available at `/docs`.

| Method | Route | Purpose |
|---|---|---|
| POST | `/auth/register` | Create an analyst account (password minimum 10 characters) |
| POST | `/auth/login` | Authenticate and receive an expiring bearer token |
| GET | `/auth/me` | Return the current authenticated user |
| GET | `/dashboard/metrics` | Dashboard cards, activity series, risk distribution |
| POST | `/dataset/upload` | Validate and import a multipart CSV (`file`) |
| GET | `/dataset/summary` | Row count, fraud-label count/rate, amount sum |
| POST | `/transactions/ingest` | Store one validated external event; requires an analyst/admin bearer token |
| POST | `/transactions/ingest/batch` | Store 1–500 external events with duplicate-ID protection |
| GET | `/transactions/live` | List recent non-CSV events |
| POST | `/transactions/analyze-batch` | Analyze up to 500 previously unassessed historical CSV records |
| POST | `/transactions/simulator/start` | Start clearly tagged local demo traffic (`normal`, `suspicious`, or `mixed`) |
| POST | `/transactions/simulator/stop` | Stop the demo transaction generator |
| GET | `/transactions/simulator/status` | Read generator state and generated-event count |
| GET | `/transactions/` | Paginated list; optional `q`, `transaction_type`, `risk_level`, `fraud_only`, `offset`, `limit` |
| GET | `/transactions/{id}` | Transaction detail and any risk result |
| POST | `/transactions/{id}/analyze` | Score with the trained PaySim model, persist the result, and create a high-risk alert when applicable |
| GET | `/predictions/{transaction_id}` | Retrieve a saved risk result by source transaction ID |
| GET | `/alerts/` | Alert queue; optional `status` |
| PATCH | `/alerts/{alert_id}?status=` | Set `open`, `acknowledged`, or `resolved` |
| GET | `/accounts/{account_id}/behavior` | Summarize observed incoming/outgoing account history |
| GET | `/accounts/{account_id}/network` | Bounded account network traversal; `depth=1..3` selects direct to multi-hop relationships |
| GET | `/cases/` | Case list; optional status |
| POST | `/cases/` | Create case |
| PATCH | `/cases/{case_id}` | Update case metadata/status |
| POST | `/cases/{case_id}/notes` | Append a validated investigation note |
| GET | `/reports/` | List reports |
| POST | `/reports/` | Create a report; generates a summary if content is omitted |
| GET | `/reports/{report_id}` | Report detail |

JSON errors use FastAPI's standard `detail` shape. Upload validation returns 4xx responses for unsupported files, oversized content, missing required headers, and malformed numeric values. List endpoints are bounded; transaction `limit` cannot exceed 100.

The analysis route returns HTTP 503 with setup guidance when a trained model artifact is unavailable. Risk explanations list the strongest feature contributions; account-network relationships are not model inputs.

## Transaction ingestion

The ingestion endpoints accept JSON transaction records, including `transaction_id`/`transactionId` and `transaction_type`/`type` field spellings. Event IDs are unique; re-sending an ID is idempotent and reports it as a duplicate rather than inserting another row. Batch size is limited to 500. New records are tagged with their source (`external` or `simulator`); existing and uploaded CSV records are tagged `csv`.

CSV uploads may include an `isFraud` ground-truth column. Accepted nonblank values are `1`/`true`/`yes` and `0`/`false`/`no`; blank or absent values are unknown, not legitimate, and invalid nonblank values reject the upload. `label_known` is exposed with transaction records so consumers can distinguish a known legitimate label from an unlabeled event. Label filters, dashboard counts, and investigation reports use only known labels.

All ingestion and simulator-control routes require a signed analyst or administrator bearer token. Each newly ingested event is assessed using the active calibrated logistic model and a separate Isolation Forest anomaly signal, then the saved assessment is returned with its status. High-risk assessments create one idempotent open alert per transaction for analyst review. Historical CSV batch assessments use the same alert rule. When fewer than 50 preceding historical CSV transactions exist, the anomaly model is explicitly marked `insufficient_history`; it does not reuse fraud probability as an anomaly score. Sender behavior is compared only after at least 5 prior outgoing events; an amount at least 5x the prior median is reported as evidence, not proof of fraud. Model risk, anomaly score, and behavioral findings remain separate and are not combined into an unvalidated score. Incoming labels such as `is_fraud` are not accepted: ground-truth labels must not be confused with model predictions.

Risk assessments expose `model_classification` (`fraud` or `legitimate`) based on the trained artifact's `classification_threshold`, separately from the CSV `isFraud` ground-truth label. This classification is model output, not proof of fraud or authorization to take an automatic payment action.

`GET /transactions/live` exposes recent external and simulator events. The dashboard refreshes its aggregate metrics, recent live transactions, and recent alerts every five seconds. Analysts can acknowledge or resolve alerts from the dashboard. `POST /transactions/analyze-batch?limit=100` explicitly analyzes up to 500 historical CSV transactions without a saved assessment and skips previously assessed rows.

Start the demo simulator with `POST /api/transactions/simulator/start`, for example `{"interval_seconds": 2, "scenario": "mixed"}`. Demo events are synthetic, passed through the same analysis pipeline, and clearly tagged; a high-amount demo scenario is not a fraud label or a model decision. Use `/stop` and `/status` to control and inspect it. The simulator is stopped when the API shuts down.

Only structured CSV upload and JSON event records are supported as transaction inputs. Arbitrary documents or binary file formats are not interpreted as transaction data.
## SafePay Assistant chatbot

- `GET /api/chat/health` — reports chatbot route status and selected provider.
- `POST /api/chat` — accepts `message`, optional `history`, optional `transaction_context`, and optional `comparison_context`.
- If the message contains one or two transaction identifiers matching the `TX...` or `TXN...` pattern, the API looks them up in the SafePay database and supplies the matching transaction and stored risk assessment. Unknown IDs receive an explicit not-found response; the assistant does not fabricate records.
- Default provider: `CHATBOT_PROVIDER=rules`. Optional local Ollama provider: `CHATBOT_PROVIDER=ollama`, `OLLAMA_URL`, and `OLLAMA_MODEL`.
- A high score is an investigation signal, not proof of fraud.

Dataset upload and transaction model analysis require `admin` or `analyst` roles. Self-registration creates `analyst` accounts. Bootstrap the first admin using `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the backend environment before startup.
