import pandas as pd


def create_features(data):
    """
    Create useful features for fraud detection.
    """

    data = data.copy()

    # Check required columns
    required_columns = [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest"
]

    for column in required_columns:
        if column not in data.columns:
            raise ValueError(
                f"Missing required column: {column}"
            )

    # Convert transaction types into numbers
    transaction_types = {
        "CASH_IN": 0,
        "CASH_OUT": 1,
        "DEBIT": 2,
        "PAYMENT": 3,
        "TRANSFER": 4
    }

    data["type_encoded"] = (
        data["type"].map(transaction_types).fillna(-1)
    )

    # Calculate origin balance difference
    data["origin_balance_change"] = (
        data["oldbalanceOrg"] - data["newbalanceOrig"]
    )

    # Calculate destination balance difference
    data["destination_balance_change"] = (
        data["newbalanceDest"] - data["oldbalanceDest"]
    )

    # Calculate amount compared to origin balance
    data["amount_to_balance_ratio"] = (
        data["amount"] /
        (data["oldbalanceOrg"] + 1)
    )

    # Identify unusual balance changes
    data["origin_balance_error"] = (
        data["origin_balance_change"] - data["amount"]
    )

    # Select useful features
    features = data[
        [
            "step",
            "amount",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
            "type_encoded",
            "origin_balance_change",
            "destination_balance_change",
            "amount_to_balance_ratio",
            "origin_balance_error"
        ]
    ].copy()

    return features