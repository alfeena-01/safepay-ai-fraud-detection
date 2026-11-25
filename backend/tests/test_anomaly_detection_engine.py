
import pandas as pd
import pytest

from app.services.anomaly_detection_engine import (
    prepare_anomaly_features,
    train_anomaly_model,
    detect_transaction_anomaly,
    calculate_anomaly_score,
    save_anomaly_model,
    load_anomaly_model,
)


@pytest.fixture
def sample_transactions():
    records = []

    for i in range(1, 101):
        records.append({
            "transaction_id": f"TX{i:04d}",
            "step": i,
            "type": "PAYMENT",
            "amount": 100 + (i % 10) * 5,
            "oldbalanceOrg": 10000 - i * 10,
            "newbalanceOrig": 9900 - i * 10,
            "oldbalanceDest": 2000,
            "newbalanceDest": 2100,
            "isFraud": 0,
            "isFlaggedFraud": 0,
        })

    return pd.DataFrame(records)


def test_prepare_anomaly_features(sample_transactions):
    features = prepare_anomaly_features(sample_transactions)

    assert not features.empty
    assert "amount" in features.columns
    assert "transaction_type_code" in features.columns

    # Labels and account identifiers must not become model features.
    assert "isFraud" not in features.columns
    assert "isFlaggedFraud" not in features.columns
    assert "transaction_id" not in features.columns


def test_train_anomaly_model(sample_transactions):
    bundle = train_anomaly_model(sample_transactions)

    assert "model" in bundle
    assert "imputer" in bundle
    assert "reference_scores" in bundle
    assert len(bundle["reference_scores"]) == len(sample_transactions)


def test_detect_transaction_anomaly(sample_transactions):
    bundle = train_anomaly_model(sample_transactions)

    results = detect_transaction_anomaly(
        sample_transactions.head(5),
        bundle,
    )

    assert len(results) == 5

    for result in results:
        assert "transaction_id" in result
        assert "anomaly_score" in result
        assert "anomaly_detected" in result
        assert "anomaly_reason" in result

        assert 0.0 <= result["anomaly_score"] <= 1.0
        assert isinstance(result["anomaly_detected"], bool)


def test_single_transaction_prediction(sample_transactions):
    bundle = train_anomaly_model(sample_transactions)

    transaction = sample_transactions.iloc[0].to_dict()

    result = detect_transaction_anomaly(transaction, bundle)

    assert isinstance(result, dict)
    assert result["transaction_id"] == "TX0001"


def test_calculate_anomaly_score():
    reference_scores = [-0.5, -0.2, 0.0, 0.2, 0.5]

    score = calculate_anomaly_score(
        -0.5,
        reference_scores,
    )

    assert 0.0 <= score <= 1.0
    assert score == 0.8


def test_save_and_load_model(sample_transactions, tmp_path):
    bundle = train_anomaly_model(sample_transactions)

    model_path = tmp_path / "anomaly_model.joblib"

    saved_path = save_anomaly_model(bundle, model_path)

    assert model_path.exists()
    assert saved_path == str(model_path)

    loaded_bundle = load_anomaly_model(model_path)

    results = detect_transaction_anomaly(
        sample_transactions.head(3),
        loaded_bundle,
    )

    assert len(results) == 3


def test_empty_transaction_data():
    with pytest.raises(ValueError):
        prepare_anomaly_features(pd.DataFrame())


def test_missing_amount_column():
    invalid_data = pd.DataFrame({
        "step": [1, 2],
        "type": ["PAYMENT", "TRANSFER"],
    })

    with pytest.raises(ValueError):
        prepare_anomaly_features(invalid_data)


def test_invalid_contamination(sample_transactions):
    with pytest.raises(ValueError):
        train_anomaly_model(
            sample_transactions,
            contamination=0.8,
        )


def test_negative_transaction_amount():
    invalid_data = pd.DataFrame({
        "amount": [-100, 200],
    })

    with pytest.raises(ValueError):
        prepare_anomaly_features(invalid_data)
