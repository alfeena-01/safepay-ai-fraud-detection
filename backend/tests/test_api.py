from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.main import app


def build_client():
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
    return TestClient(app), test_engine


def test_dataset_transaction_risk_case_report_workflow():
    client, test_engine = build_client()
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
    client.close()
    test_engine.dispose()
    app.dependency_overrides.clear()


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
