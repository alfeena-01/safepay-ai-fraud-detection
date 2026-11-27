from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.transactions as transactions_api
from app.database.connection import Base, get_db, migrate_schema
from app.main import app
from app.services.anomaly_detection_engine.model import ModelUnavailableError


def build_client(monkeypatch=None):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.state.auth_disabled = True
    if monkeypatch is not None:
        monkeypatch.setattr(
            transactions_api,
            "assess_transaction",
            lambda transaction: {
                "fraud_probability": 0.9,
                "anomaly_score": 0.9,
                "graph_risk": 0.0,
                "overall_risk_score": 90.0,
                "risk_level": "high",
                "explanation": "Test assessment.",
                "recommended_action": "Escalate for analyst review",
                "model_version": "test-model-v1",
            },
        )
    return TestClient(app), test_engine


def test_dataset_transaction_risk_case_report_workflow(monkeypatch):
    client, test_engine = build_client(monkeypatch)
    csv_content = (
        "transactionId,step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,"
        "nameDest,oldbalanceDest,newbalanceDest,isFraud\n"
        "tx-001,1,CASH_OUT,150000,acct-a,150000,0,acct-b,0,150000,0\n"
        "tx-002,2,PAYMENT,25,acct-b,150000,149975,acct-c,0,25,0\n"
    )
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["inserted"] == 2
    assert client.post(
        "/api/dataset/upload",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    ).json()["duplicates_skipped"] == 2

    rows = client.get("/api/transactions/", params={"q": "tx-001"}).json()
    assert len(rows) == 1
    assert len(client.get("/api/transactions/", params={"fraud_only": "false"}).json()) == 2
    assert client.get("/api/transactions/", params={"fraud_only": "true"}).json() == []
    transaction_id = rows[0]["id"]
    risk = client.post(f"/api/transactions/{transaction_id}/analyze")
    assert risk.status_code == 200
    assert risk.json()["risk_level"] == "high"
    assert client.get("/api/transactions/", params={"risk_level": "high"}).json()[0]["id"] == transaction_id
    assert client.get("/api/predictions/tx-001").status_code == 200
    alert = client.get("/api/alerts/").json()[0]
    assert alert["transaction_id"] == transaction_id
    assert client.patch(f"/api/alerts/{alert['id']}", params={"status": "acknowledged"}).json()["status"] == "acknowledged"

    case = client.post("/api/cases/", json={
        "title": "Review high-risk transfer",
        "transaction_id": transaction_id,
        "priority": "high",
    })
    assert case.status_code == 201
    case_id = case.json()["id"]
    assert client.post(f"/api/cases/{case_id}/notes", json={"note": "Check beneficiary"}).status_code == 200
    assert client.patch(f"/api/cases/{case_id}", json={"status": "in_progress"}).json()["status"] == "in_progress"

    report = client.post("/api/reports/", json={
        "title": "Transfer review",
        "case_id": case_id,
        "transaction_id": transaction_id,
    })
    assert report.status_code == 201
    assert "Risk assessment: high" in report.json()["content"]
    assert client.get(f"/api/reports/{report.json()['id']}").status_code == 200
    assert len(client.get("/api/reports/").json()) == 1
    assert client.get("/api/dashboard/metrics").json()["total_transactions"] == 2
    assert client.get("/api/accounts/acct-a/network").json()["connected_accounts"][0]["account_id"] == "acct-b"
    two_hop = client.get("/api/accounts/acct-a/network", params={"depth": 2}).json()
    assert two_hop["depth"] == 2
    assert {item["account_id"] for item in two_hop["connected_accounts"]} == {"acct-b", "acct-c"}
    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_invalid_dataset_headers_are_rejected():
    client, test_engine = build_client()
    response = client.post(
        "/api/dataset/upload",
        files={"file": ("invalid.csv", "foo,bar\n1,2\n", "text/csv")},
    )
    assert response.status_code == 422
    assert "Missing required CSV columns" in response.json()["detail"]
    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_csv_ground_truth_labels_distinguish_unknown_from_legitimate():
    client, test_engine = build_client()
    uploaded = client.post(
        "/api/dataset/upload",
        files={
            "file": (
                "labels.csv",
                "transactionId,type,amount,nameOrig,nameDest,isFraud\n"
                "fraud-1,TRANSFER,100,a,b,1\n"
                "legit-1,PAYMENT,25,c,d,0\n"
                "unknown-1,PAYMENT,10,e,f,\n",
                "text/csv",
            )
        },
    )
    assert uploaded.status_code == 200
    records = {
        row["transaction_id"]: row
        for row in client.get("/api/transactions/").json()
    }
    assert records["fraud-1"]["label_known"] is True
    assert records["fraud-1"]["is_fraud"] is True
    assert records["legit-1"]["label_known"] is True
    assert records["legit-1"]["is_fraud"] is False
    assert records["unknown-1"]["label_known"] is False
    assert records["unknown-1"]["is_fraud"] is False
    assert {row["transaction_id"] for row in client.get(
        "/api/transactions/", params={"fraud_only": "true"}
    ).json()} == {"fraud-1"}
    assert {row["transaction_id"] for row in client.get(
        "/api/transactions/", params={"fraud_only": "false"}
    ).json()} == {"legit-1"}
    summary = client.get("/api/dataset/summary").json()
    assert summary["labeled_transactions"] == 2
    assert summary["fraud_transactions"] == 1
    assert summary["legitimate_transactions"] == 1

    invalid = client.post(
        "/api/dataset/upload",
        files={
            "file": (
                "invalid-label.csv",
                "type,amount,nameOrig,nameDest,isFraud\nPAYMENT,5,a,b,sometimes\n",
                "text/csv",
            )
        },
    )
    assert invalid.status_code == 422
    assert client.get("/api/dataset/summary").json()["total_transactions"] == 3
    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_analysis_reports_missing_model_as_service_unavailable(monkeypatch):
    client, test_engine = build_client()

    def missing_model(_transaction):
        raise ModelUnavailableError("Install the trained model.")

    monkeypatch.setattr(transactions_api, "assess_transaction", missing_model)
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": (
            "sample.csv",
            "type,amount,nameOrig,nameDest\nTRANSFER,100,acct-a,acct-b\n",
            "text/csv",
        )},
    )
    transaction_id = client.get("/api/transactions/").json()[0]["id"]
    response = client.post(f"/api/transactions/{transaction_id}/analyze")
    assert uploaded.status_code == 200
    assert response.status_code == 503
    assert response.json()["detail"] == "Install the trained model."
    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_analysis_endpoint_returns_trained_model_explanation():
    client, test_engine = build_client()
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": (
            "sample.csv",
            "type,amount,nameOrig,nameDest,step,oldbalanceOrg,newbalanceOrig,"
            "oldbalanceDest,newbalanceDest\nTRANSFER,1250,acct-a,acct-b,3,2000,750,20,1270\n",
            "text/csv",
        )},
    )
    transaction_id = client.get("/api/transactions/").json()[0]["id"]
    response = client.post(f"/api/transactions/{transaction_id}/analyze")
    assert uploaded.status_code == 200
    assert response.status_code == 200
    assert response.json()["model_version"] == "safepay-logistic-paysim-v1"
    assert response.json()["model_classification"] in {"fraud", "legitimate"}
    assert 0.0 <= response.json()["classification_threshold"] <= 1.0
    listed = client.get("/api/transactions/").json()[0]
    assert listed["risk_assessment"]["model_classification"] == response.json()["model_classification"]
    assert "Top model signals" in response.json()["explanation"]
    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_missing_csv_values_are_normalized_and_non_finite_values_rejected():
    client, test_engine = build_client()
    missing = client.post(
        "/api/dataset/upload",
        files={"file": (
            "missing.csv",
            "type,amount,nameOrig,nameDest,step\nTRANSFER,NaN,NaN,none,NaN\n",
            "text/csv",
        )},
    )
    assert missing.status_code == 200
    row = client.get("/api/transactions/").json()[0]
    assert row["amount"] == 0
    assert row["name_orig"] is None
    assert row["name_dest"] is None
    assert row["step"] is None
    duplicate = client.post(
        "/api/dataset/upload",
        files={"file": (
            "missing.csv",
            "type,amount,nameOrig,nameDest,step\nTRANSFER,NaN,NaN,none,NaN\n",
            "text/csv",
        )},
    )
    assert duplicate.json()["duplicates_skipped"] == 1

    invalid = client.post(
        "/api/dataset/upload",
        files={"file": (
            "infinite.csv",
            "transactionId,type,amount,nameOrig,nameDest\nbad-1,TRANSFER,Infinity,a,b\n",
            "text/csv",
        )},
    )
    assert invalid.status_code == 422
    assert client.get("/api/dataset/summary").json()["total_transactions"] == 1
    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_live_transaction_ingestion_is_idempotent_and_separate_from_csv():
    client, test_engine = build_client()
    event = {
        "transactionId": "external-001",
        "step": 42,
        "type": "transfer",
        "amount": 1250.5,
        "nameOrig": "sender-1",
        "nameDest": "receiver-1",
        "created_at": "2026-01-02T03:04:05Z",
    }

    received = client.post("/api/transactions/ingest", json=event)
    duplicate = client.post("/api/transactions/ingest", json=event)

    assert received.status_code == 200
    assert received.json()["inserted"] is True
    assert received.json()["source"] == "external"
    assert received.json()["analysis_status"] == "complete"
    risk = received.json()["risk_assessment"]
    assert 0.0 <= risk["fraud_probability"] <= 1.0
    assert risk["anomaly_status"] == "insufficient_history"
    assert risk["behavior_status"] == "insufficient_history"
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["analysis_status"] == "complete"
    live = client.get("/api/transactions/live").json()
    assert len(live) == 1
    assert live[0]["transaction_type"] == "TRANSFER"
    assert live[0]["source"] == "external"
    assert live[0]["risk_assessment"]["fraud_probability"] == risk["fraud_probability"]
    assert live[0]["created_at"].startswith("2026-01-02T03:04:05")

    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_high_risk_ingestion_creates_one_explainable_alert(monkeypatch):
    client, test_engine = build_client(monkeypatch)
    event = {
        "transaction_id": "high-risk-live-001",
        "transaction_type": "TRANSFER",
        "amount": 50000,
        "name_orig": "sender-high",
        "name_dest": "receiver-high",
    }

    received = client.post("/api/transactions/ingest", json=event)
    duplicate = client.post("/api/transactions/ingest", json=event)

    assert received.status_code == 200
    assert received.json()["risk_assessment"]["risk_level"] == "high"
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    alerts = client.get("/api/alerts/").json()
    assert len(alerts) == 1
    assert alerts[0]["transaction_ref"] == event["transaction_id"]
    assert alerts[0]["status"] == "open"
    assert alerts[0]["risk_level"] == "high"
    assert alerts[0]["explanation"]

    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_high_risk_historical_assessment_creates_alert(monkeypatch):
    client, test_engine = build_client(monkeypatch)
    uploaded = client.post(
        "/api/dataset/upload",
        files={
            "file": (
                "historical.csv",
                "transactionId,type,amount,nameOrig,nameDest\n"
                "historical-high-001,TRANSFER,50000,sender,receiver\n",
                "text/csv",
            )
        },
    )
    assessment = client.post("/api/transactions/analyze-batch")
    assert uploaded.status_code == 200
    assert assessment.status_code == 200
    assert assessment.json()["analyzed"] == 1
    alerts = client.get("/api/alerts/").json()
    assert len(alerts) == 1
    assert alerts[0]["transaction_ref"] == "historical-high-001"

    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_batch_ingestion_deduplicates_and_rejects_invalid_events():
    client, test_engine = build_client()
    event = {
        "transaction_id": "batch-001",
        "transaction_type": "PAYMENT",
        "amount": 40,
        "name_orig": "sender",
        "name_dest": "receiver",
    }

    result = client.post(
        "/api/transactions/ingest/batch",
        json={"transactions": [event, event]},
    )
    assert result.status_code == 200
    assert result.json()["received"] == 2
    assert result.json()["inserted"] == 1
    assert result.json()["duplicates_skipped"] == 1
    assert result.json()["analyzed"] == 2
    assert result.json()["transactions"][0]["risk_assessment"] is not None

    invalid_amount = {**event, "transaction_id": "bad-amount", "amount": -1}
    invalid_label = {**event, "transaction_id": "bad-label", "is_fraud": True}
    assert client.post("/api/transactions/ingest", json=invalid_amount).status_code == 422
    assert client.post("/api/transactions/ingest", json=invalid_label).status_code == 422
    assert len(client.get("/api/transactions/live").json()) == 1

    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_simulator_can_start_report_status_and_stop(monkeypatch):
    client, test_engine = build_client()
    test_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(transactions_api, "SessionLocal", test_session)

    started = client.post(
        "/api/transactions/simulator/start",
        json={"interval_seconds": 1, "scenario": "mixed"},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "running"
    assert client.get("/api/transactions/simulator/status").json()["scenario"] == "mixed"
    demo_transactions = client.get("/api/transactions/live").json()
    assert len(demo_transactions) == 1
    assert demo_transactions[0]["source"] == "simulator"
    assert demo_transactions[0]["risk_assessment"] is not None

    stopped = client.post("/api/transactions/simulator/stop")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"
    assert client.get("/api/transactions/simulator/status").json()["status"] == "stopped"

    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_transaction_source_migration_preserves_existing_rows():
    legacy_engine = create_engine("sqlite://")
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE transactions (id INTEGER PRIMARY KEY, transaction_id VARCHAR(128))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE risk_assessments (id INTEGER PRIMARY KEY)"
        )
        connection.exec_driver_sql(
            "INSERT INTO transactions (id, transaction_id) VALUES (1, 'legacy-001')"
        )

    migrate_schema(legacy_engine)

    with legacy_engine.connect() as connection:
        source = connection.exec_driver_sql(
            "SELECT source FROM transactions WHERE id = 1"
        ).scalar_one()
        transaction_columns = {
            row[1] for row in connection.exec_driver_sql(
                "PRAGMA table_info(transactions)"
            ).fetchall()
        }
        assessment_columns = {
            row[1] for row in connection.exec_driver_sql(
                "PRAGMA table_info(risk_assessments)"
            ).fetchall()
        }
    assert source == "csv"
    assert "label_known" in transaction_columns
    assert {
        "model_classification",
        "classification_threshold",
        "anomaly_status",
        "anomaly_reason",
        "behavior_status",
        "behavior_findings",
    }.issubset(assessment_columns)
    legacy_engine.dispose()


def test_ingestion_requires_authentication():
    app.state.auth_disabled = False
    client = TestClient(app)
    response = client.post(
        "/api/transactions/ingest",
        json={
            "transaction_id": "unauthorized-001",
            "transaction_type": "PAYMENT",
            "amount": 10,
        },
    )
    assert response.status_code == 401
    client.close()


def test_historical_csv_batch_analysis_uses_prior_sender_history():
    client, test_engine = build_client()
    rows = ["transactionId,step,type,amount,nameOrig,nameDest"]
    rows.extend(
        f"history-{index},{index},PAYMENT,{amount},sender-1,receiver-{index}"
        for index, amount in enumerate([100, 100, 100, 100, 100, 1000], start=1)
    )
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("history.csv", "\n".join(rows), "text/csv")},
    )
    assert uploaded.status_code == 200

    analysis = client.post("/api/transactions/analyze-batch", params={"limit": 20})
    assert analysis.status_code == 200
    assert analysis.json()["analyzed"] == 6
    final_assessment = client.get("/api/transactions/6").json()["risk_assessment"]
    assert final_assessment["behavior_status"] == "available"
    assert final_assessment["behavior_findings"]
    assert "10.0 times" in final_assessment["behavior_findings"][0]
    assert final_assessment["anomaly_status"] == "insufficient_history"

    repeated = client.post("/api/transactions/analyze-batch")
    assert repeated.json()["analyzed"] == 0
    behavior = client.get("/api/accounts/sender-1/behavior").json()
    assert behavior["outgoing"]["transaction_count"] == 6
    assert behavior["outgoing"]["maximum_amount"] == 1000

    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_incoming_transaction_uses_trained_independent_anomaly_model():
    client, test_engine = build_client()
    rows = ["transactionId,step,type,amount,nameOrig,nameDest,oldbalanceOrg,newbalanceOrig,oldbalanceDest,newbalanceDest"]
    rows.extend(
        f"baseline-{index},{index},PAYMENT,{100 + index},sender-{index},receiver-{index},"
        f"{2000 + index},{1900},{100},{200 + index}"
        for index in range(50)
    )
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("baseline.csv", "\n".join(rows), "text/csv")},
    )
    assert uploaded.status_code == 200

    incoming = client.post(
        "/api/transactions/ingest",
        json={
            "transaction_id": "new-transaction",
            "transaction_type": "TRANSFER",
            "amount": 50000,
            "name_orig": "new-sender",
            "name_dest": "new-receiver",
        },
    )
    assert incoming.status_code == 200
    assessment = incoming.json()["risk_assessment"]
    record = client.get(
        "/api/transactions/",
        params={"q": "new-transaction"},
    ).json()[0]
    assert record["label_known"] is False
    assert record["is_fraud"] is False
    assert assessment["anomaly_status"] == "available"
    assert assessment["model_classification"] in {"fraud", "legitimate"}
    assert 0.0 <= assessment["anomaly_score"] <= 1.0
    assert assessment["anomaly_score"] != assessment["fraud_probability"]
    assert client.get("/api/alerts/").json() == []

    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False


def test_case_validation_and_missing_transaction():
    client, test_engine = build_client()
    invalid = client.post("/api/cases/", json={"title": "x", "priority": "urgent"})
    assert invalid.status_code == 422
    missing = client.post("/api/cases/", json={
        "title": "Missing transaction case",
        "transaction_id": 404,
    })
    assert missing.status_code == 404
    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()
    app.state.auth_disabled = False
