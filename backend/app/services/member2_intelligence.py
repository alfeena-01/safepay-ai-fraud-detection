
from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.anomaly_detection_engine import (
    detect_transaction_anomaly,
)
from app.services.graph_intelligence_engine import (
    build_transaction_graph,
    calculate_graph_risk,
)


def _normalize_transactions(transactions: Any) -> pd.DataFrame:
    """Normalize supported transaction inputs for both engines."""
    if isinstance(transactions, pd.DataFrame):
        df = transactions.copy()
    elif isinstance(transactions, dict):
        df = pd.DataFrame([transactions])
    elif isinstance(transactions, (list, tuple)):
        df = pd.DataFrame(list(transactions))
    else:
        raise TypeError(
            "transactions must be a DataFrame, dictionary, or list of dictionaries"
        )

    if df.empty:
        raise ValueError("Transaction data cannot be empty")

    # Support both internal field names and PaySim field names.
    aliases = {
        "nameOrig": "sender_account",
        "nameDest": "receiver_account",
        "type": "transaction_type",
    }

    for source, target in aliases.items():
        if target not in df.columns and source in df.columns:
            df[target] = df[source]

    required = {
        "sender_account",
        "receiver_account",
        "amount",
    }
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            f"Missing required transaction columns: {sorted(missing)}"
        )

    if "transaction_id" not in df.columns:
        df["transaction_id"] = [
            f"TX-{index + 1:06d}" for index in range(len(df))
        ]

    df["transaction_id"] = df["transaction_id"].astype("string").str.strip()

    if df["transaction_id"].isna().any() or df["transaction_id"].eq("").any():
        raise ValueError("Transaction IDs cannot be empty")

    if df["transaction_id"].duplicated().any():
        raise ValueError("Transaction IDs must be unique")

    return df


def analyze_member2_transactions(
    transactions: Any,
    anomaly_model_bundle: dict,
    suspicious_transaction_ids: set[str] | list[str] | tuple[str, ...] | None = None,
    activity_threshold: int = 10,
    shared_receiver_threshold: int = 3,
) -> list[dict[str, Any]]:
    """
    Run anomaly detection and graph intelligence together.

    The anomaly model must already be trained. Known suspicious transaction
    IDs from another validated detection component can optionally be supplied.

    Returns one combined investigation result per transaction.
    """
    df = _normalize_transactions(transactions)

    # Run the anomaly model on the complete transaction batch.
    anomaly_results = detect_transaction_anomaly(
        df,
        anomaly_model_bundle,
    )

    if isinstance(anomaly_results, dict):
        anomaly_results = [anomaly_results]

    anomaly_by_id = {
        str(item["transaction_id"]): item
        for item in anomaly_results
    }

    # Build one graph containing all transactions in the batch.
    graph = build_transaction_graph(df)

    externally_flagged_ids = {
        str(value) for value in (suspicious_transaction_ids or [])
    }

    anomaly_flagged_ids = {
        transaction_id
        for transaction_id, result in anomaly_by_id.items()
        if result["anomaly_detected"]
    }

    # Graph risk can use both anomaly evidence and externally supplied flags.
    combined_flagged_ids = externally_flagged_ids.union(
        anomaly_flagged_ids
    )

    combined_results = []

    for row in df.to_dict(orient="records"):
        transaction_id = str(row["transaction_id"])
        anomaly_result = anomaly_by_id.get(transaction_id)

        if anomaly_result is None:
            raise RuntimeError(
                f"Anomaly result missing for transaction {transaction_id}"
            )

        graph_result = calculate_graph_risk(
            graph=graph,
            transaction_id=transaction_id,
            suspicious_transaction_ids=combined_flagged_ids,
            activity_threshold=activity_threshold,
            shared_receiver_threshold=shared_receiver_threshold,
        )

        combined_results.append({
            "transaction_id": transaction_id,
            "sender_account": str(row.get(
                "sender_account", row.get("nameOrig")
            )),
            "receiver_account": str(row.get(
                "receiver_account", row.get("nameDest")
            )),
            "anomaly_score": float(anomaly_result["anomaly_score"]),
            "anomaly_detected": bool(anomaly_result["anomaly_detected"]),
            "anomaly_reason": anomaly_result["anomaly_reason"],
            "graph_risk": graph_result["graph_risk"],
            "graph_risk_level": graph_result["graph_risk_level"],
            "connected_accounts": graph_result["connected_accounts"],
            "suspicious_path_detected": graph_result[
                "suspicious_path_detected"
            ],
            "evidence": {
                "anomaly": anomaly_result["anomaly_reason"],
                "graph": graph_result["evidence"],
            },
        })

    return combined_results
