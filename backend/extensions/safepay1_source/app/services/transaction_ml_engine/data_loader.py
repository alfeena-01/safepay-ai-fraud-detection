import pandas as pd
from pathlib import Path


def load_transaction_data(file_path):

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    sampled_data = []

    for chunk in pd.read_csv(file_path, chunksize=100000):

        sample = chunk.sample(
            n=min(5000, len(chunk)),
            random_state=42
        )

        sampled_data.append(sample)

    data = pd.concat(sampled_data, ignore_index=True)

    if len(data) > 100000:
        data = data.sample(n=100000, random_state=42)

    if data.empty:
        raise ValueError("The dataset is empty.")

    return data


def validate_transaction_data(data):

    if data is None or data.empty:
        raise ValueError("No transaction data available.")

    required_columns = ["amount", "isFraud"]

    for column in required_columns:
        if column not in data.columns:
            raise ValueError(f"Missing required column: {column}")

    return True