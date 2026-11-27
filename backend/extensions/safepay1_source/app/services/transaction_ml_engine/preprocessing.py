import pandas as pd


def clean_transaction_data(data):
    """
    Clean transaction data before model training.
    """

    data = data.copy()

    # Remove duplicate transactions
    data = data.drop_duplicates()

    # Handle missing numerical values
    numeric_columns = data.select_dtypes(include=["number"]).columns

    for column in numeric_columns:
        data[column] = data[column].fillna(data[column].median())

    # Handle missing text values
    text_columns = data.select_dtypes(include=["object"]).columns

    for column in text_columns:
        data[column] = data[column].fillna("Unknown")

    return data


def separate_features_and_target(data):
    """
    Separate input features and fraud target.
    """

    if "isFraud" not in data.columns:
        raise ValueError("isFraud column is missing.")

    X = data.drop(columns=["isFraud"])
    y = data["isFraud"]

    return X, y