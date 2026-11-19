
"""
FINSHIELD AI - Anomaly Detection Engine
Member 2

Uses Isolation Forest to identify unusual transaction patterns.
Target and account identifier columns are never used as model features.
"""

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer


MODEL_VERSION = "1.0.0"

# Fixed feature order ensures training and prediction use identical columns.
FEATURE_COLUMNS = [
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "origin_balance_delta",
    "destination_balance_delta",
    "transaction_type_code",
]

TRANSACTION_TYPE_CODES = {
    "CASH_IN": 1,
    "CASH_OUT": 2,
    "DEBIT": 3,
    "PAYMENT": 4,
    "TRANSFER": 5,
}


def _as_dataframe(transactions: Any) -> pd.DataFrame:
    """Convert supported transaction input into a DataFrame."""

    if isinstance(transactions, pd.DataFrame):
        data = transactions.copy()
    elif isinstance(transactions, dict):
        data = pd.DataFrame([transactions])
    elif isinstance(transactions, list):
        data = pd.DataFrame(transactions)
    else:
        raise TypeError(
            "Transactions must be a pandas DataFrame, dictionary, or list."
        )

    if data.empty:
        raise ValueError("Transaction data cannot be empty.")

    return data


def _get_column(data: pd.DataFrame, names: list[str], default=0):
    """Find a column using supported dataset naming conventions."""

    for name in names:
        if name in data.columns:
            return data[name]

    return pd.Series(default, index=data.index)


def prepare_anomaly_features(transactions: Any) -> pd.DataFrame:
    """
    Prepare numerical features for Isolation Forest.

    Supports PaySim columns and common internal transaction fields.
    isFraud, isFlaggedFraud, transaction IDs, and account IDs
    are deliberately excluded.
    """

    data = _as_dataframe(transactions)

    if "amount" not in data.columns:
        raise ValueError("Transaction data must contain an amount column.")

    features = pd.DataFrame(index=data.index)

    numeric_sources = {
        "step": ["step"],
        "amount": ["amount"],
        "oldbalanceOrg": ["oldbalanceOrg", "old_balance_org"],
        "newbalanceOrig": ["newbalanceOrig", "new_balance_orig"],
        "oldbalanceDest": ["oldbalanceDest", "old_balance_dest"],
        "newbalanceDest": ["newbalanceDest", "new_balance_dest"],
    }

    for feature_name, source_names in numeric_sources.items():
        values = _get_column(data, source_names)
        features[feature_name] = pd.to_numeric(
            values, errors="coerce"
        )

    features["origin_balance_delta"] = (
        features["oldbalanceOrg"] - features["newbalanceOrig"]
    )

    features["destination_balance_delta"] = (
        features["newbalanceDest"] - features["oldbalanceDest"]
    )

    transaction_type = _get_column(
        data, ["type", "transaction_type"], default=""
    )

    features["transaction_type_code"] = (
        transaction_type.astype(str)
        .str.upper()
        .map(TRANSACTION_TYPE_CODES)
        .fillna(0)
    )

    # Preserve a consistent feature order.
    features = features[FEATURE_COLUMNS]

    # Reject records without any usable transaction amount.
    if features["amount"].isna().all():
        raise ValueError("Transaction amount contains no valid numeric values.")

    if (features["amount"].dropna() < 0).any():
        raise ValueError("Transaction amounts cannot be negative.")

    return features


def train_anomaly_model(
    transactions: Any,
    contamination: float = 0.01,
    random_state: int = 42,
) -> dict:
    """
    Train an Isolation Forest model.

    contamination represents the expected proportion of anomalies.
    It is a model configuration, not a measured fraud rate.
    """

    if not 0 < contamination <= 0.5:
        raise ValueError("Contamination must be greater than 0 and at most 0.5.")

    features = prepare_anomaly_features(transactions)

    if len(features) < 2:
        raise ValueError("At least two transactions are required for training.")

    imputer = SimpleImputer(
        strategy="median",
        keep_empty_features=True,
    )

    transformed_features = imputer.fit_transform(features)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )

    model.fit(transformed_features)

    # Isolation Forest: lower decision scores indicate more unusual records.
    reference_scores = np.sort(model.decision_function(transformed_features))

    threshold = float(
        np.quantile(reference_scores, contamination)
    )

    return {
        "model_version": MODEL_VERSION,
        "model": model,
        "imputer": imputer,
        "feature_columns": FEATURE_COLUMNS.copy(),
        "reference_scores": reference_scores,
        "threshold": threshold,
        "contamination": contamination,
    }


def calculate_anomaly_score(
    decision_score: float,
    reference_scores: np.ndarray,
) -> float:
    """
    Convert a decision score into an anomaly score between 0 and 1.

    More unusual scores receive higher anomaly scores.
    The reference distribution comes from training transactions.
    """

    reference = np.asarray(reference_scores, dtype=float)

    if reference.size == 0:
        raise ValueError("Reference scores cannot be empty.")

    if not np.isfinite(decision_score):
        raise ValueError("Decision score must be finite.")

    if not np.isfinite(reference).all():
        raise ValueError("Reference scores must contain finite values.")

    percentile = np.searchsorted(
        reference,
        decision_score,
        side="right",
    ) / len(reference)

    anomaly_score = 1.0 - percentile

    return float(np.clip(anomaly_score, 0.0, 1.0))


def detect_transaction_anomaly(
    transactions: Any,
    model_bundle: dict,
):
    """
    Detect unusual transactions.

    A single dictionary returns one dictionary.
    A DataFrame or list returns a list of result dictionaries.
    """

    required_keys = {
        "model",
        "imputer",
        "reference_scores",
        "threshold",
        "feature_columns",
    }

    if not isinstance(model_bundle, dict):
        raise TypeError("Model bundle must be a dictionary.")

    if not required_keys.issubset(model_bundle):
        raise ValueError("Invalid or incomplete anomaly model bundle.")

    single_record = isinstance(transactions, dict)

    data = _as_dataframe(transactions)
    features = prepare_anomaly_features(data)

    transformed_features = model_bundle["imputer"].transform(
        features[model_bundle["feature_columns"]]
    )

    model = model_bundle["model"]

    decision_scores = model.decision_function(transformed_features)

    results = []

    for index, decision_score in enumerate(decision_scores):
        anomaly_score = calculate_anomaly_score(
            float(decision_score),
            model_bundle["reference_scores"],
        )

        anomaly_detected = bool(
            decision_score <= model_bundle["threshold"]
        )

        if anomaly_detected:
            reason = (
                "Transaction pattern differs from the reference distribution"
            )
        else:
            reason = (
                "Transaction pattern is within the reference distribution"
            )

        transaction_id = (
            data.iloc[index].get("transaction_id")
            or data.iloc[index].get("id")
            or f"TX-{index + 1:06d}"
        )

        results.append({
            "transaction_id": str(transaction_id),
            "anomaly_score": anomaly_score,
            "anomaly_detected": anomaly_detected,
            "anomaly_reason": reason,
        })

    return results[0] if single_record else results


def save_anomaly_model(
    model_bundle: dict,
    model_path: str | Path,
) -> str:
    """Save the trained model bundle to disk."""

    required_keys = {
        "model",
        "imputer",
        "reference_scores",
        "threshold",
        "feature_columns",
    }

    if not isinstance(model_bundle, dict):
        raise TypeError("Model bundle must be a dictionary.")

    if not required_keys.issubset(model_bundle):
        raise ValueError("Cannot save an incomplete model bundle.")

    path = Path(model_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model_bundle, path)

    return str(path)


def load_anomaly_model(model_path: str | Path) -> dict:
    """Load a previously saved anomaly model bundle."""

    path = Path(model_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Anomaly model not found: {path}"
        )

    bundle = joblib.load(path)

    required_keys = {
        "model",
        "imputer",
        "reference_scores",
        "threshold",
        "feature_columns",
    }

    if not isinstance(bundle, dict) or not required_keys.issubset(bundle):
        raise ValueError("The saved file is not a valid anomaly model bundle.")

    return bundle
