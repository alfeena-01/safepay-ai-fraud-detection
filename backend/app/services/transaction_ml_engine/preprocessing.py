import pandas as pd


def clean_dataset(data):
    """
    Clean transaction dataset.
    """

    data = data.copy()

    # Check required target column
    if "isFraud" not in data.columns:
        raise ValueError("Dataset must contain isFraud column")

    # Remove duplicate transactions
    data = data.drop_duplicates()

    # Remove rows with missing target values
    data = data.dropna(subset=["isFraud"])

    # Handle missing numerical values
    numerical_columns = data.select_dtypes(
        include=["number"]
    ).columns

    for column in numerical_columns:
        if data[column].isnull().any():
            median_value = data[column].median()
            data[column] = data[column].fillna(median_value)

    # Handle missing categorical values
    categorical_columns = data.select_dtypes(
        include=["object"]
    ).columns

    for column in categorical_columns:
        if data[column].isnull().any():
            mode_values = data[column].mode()

            if not mode_values.empty:
                data[column] = data[column].fillna(mode_values[0])

    return data


def check_missing_values(data):
    return data.isnull().sum()


def get_cleaning_summary(data):
    return {
        "total_rows": len(data),
        "total_columns": len(data.columns),
        "duplicates": int(data.duplicated().sum()),
        "missing_values": int(data.isnull().sum().sum())
    }