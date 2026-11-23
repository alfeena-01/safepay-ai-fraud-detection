
import pandas as pd
import pytest

from app.services.anomaly_detection_engine import train_anomaly_model
from app.services.member2_intelligence import analyze_member2_transactions


@pytest.fixture
def sample_transactions():
    records = []

    for i in range(1, 101):
        records.append({
            "transaction_id": f"TX{i:04d}",
            "step": i,
            "type": "PAYMENT",
            "amount": 100 + (i % 10) * 5,
            "nameOrig": f"ACCOUNT-{i}",
            "nameDest": "COMMON-RECEIVER",
            "oldbalanceOrg": 10000 - i * 10,
            "newbalanceOrig": 9900 - i * 10,
            "oldbalanceDest": 2000,
            "newbalanceDest": 2100,
        })

    return pd.DataFrame(records)


@pytest.fixture
def trained_model(sample_transactions):
    return train_anomaly_model(sample_transactions)


def test_combined_engine_returns_one_result_per_transaction(
    sample_transactions,
    trained_model,
):
    results = analyze_member2_transactions(
        sample_transactions.head(5),
        trained_model,
    )

    assert len(results) == 5


def test_combined_engine_has_required_output_fields(
    sample_transactions,
    trained_model,
):
    results = analyze_member2_transactions(
        sample_transactions.head(3),
        trained_model,
    )

    required_fields = {
        "transaction_id",
        "sender_account",
        "receiver_account",
        "anomaly_score",
        "anomaly_detected",
        "anomaly_reason",
        "graph_risk",
        "graph_risk_level",
        "connected_accounts",
        "suspicious_path_detected",
        "evidence",
    }

    for result in results:
        assert required_fields.issubset(result.keys())
        assert 0.0 <= result["anomaly_score"] <= 1.0
        assert 0.0 <= result["graph_risk"] <= 1.0
        assert result["graph_risk_level"] in {"low", "medium", "high"}


def test_combined_engine_accepts_paysim_columns(
    sample_transactions,
    trained_model,
):
    results = analyze_member2_transactions(
        sample_transactions.head(2),
        trained_model,
    )

    assert results[0]["sender_account"] == "ACCOUNT-1"
    assert results[0]["receiver_account"] == "COMMON-RECEIVER"


def test_external_suspicious_transaction_ids_are_accepted(
    sample_transactions,
    trained_model,
):
    results = analyze_member2_transactions(
        sample_transactions.head(3),
        trained_model,
        suspicious_transaction_ids=["TX0001"],
    )

    assert len(results) == 3
    assert all("evidence" in result for result in results)


def test_empty_input_is_rejected(trained_model):
    with pytest.raises(ValueError):
        analyze_member2_transactions(
            pd.DataFrame(),
            trained_model,
        )


def test_missing_account_columns_are_rejected(trained_model):
    invalid_data = pd.DataFrame({
        "transaction_id": ["TX001"],
        "amount": [100],
    })

    with pytest.raises(ValueError):
        analyze_member2_transactions(
            invalid_data,
            trained_model,
        )


def test_duplicate_transaction_ids_are_rejected(
    sample_transactions,
    trained_model,
):
    duplicate_data = sample_transactions.head(2).copy()
    duplicate_data.iloc[1, duplicate_data.columns.get_loc(
        "transaction_id"
    )] = "TX0001"

    with pytest.raises(ValueError):
        analyze_member2_transactions(
            duplicate_data,
            trained_model,
        )
