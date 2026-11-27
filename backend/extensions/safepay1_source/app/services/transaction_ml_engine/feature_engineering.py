import pandas as pd


def create_transaction_features(data):
    """
    Create additional features for fraud detection.
    """

    data = data.copy()

    if "amount" in data.columns:
        data["amount_log"] = (data["amount"].clip(lower=0) + 1).apply(
            lambda value: __import__("math").log1p(value - 1)
        )

    if "type" in data.columns:
        data["transaction_type"] = data["type"].astype("category").cat.codes

    if "oldbalanceOrg" in data.columns and "newbalanceOrig" in data.columns:
        data["balance_difference"] = (
            data["oldbalanceOrg"] - data["newbalanceOrig"]
        )

    return data