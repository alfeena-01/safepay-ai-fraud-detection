import pandas as pd
from pathlib import Path


def load_dataset(file_path):
    """
    Load transaction data using memory-friendly chunk sampling.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    print("Loading dataset in small chunks...")

    sample_chunks = []

    columns = [
        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "isFraud"
    ]

    for chunk_number, chunk in enumerate(
        pd.read_csv(
            file_path,
            usecols=columns,
            chunksize=500000
        )
    ):

        sample = chunk.sample(
            frac=0.08,
            random_state=42 + chunk_number
        )

        sample_chunks.append(sample)

        print(f"Processed chunk: {chunk_number + 1}")

    if not sample_chunks:
        raise ValueError("No transaction data found!")

    data = pd.concat(
        sample_chunks,
        ignore_index=True
    )

    print("\nDataset loaded successfully!")
    print("Total transactions:", len(data))
    print("Fraud transactions:", int(data["isFraud"].sum()))
    print(
        "Legitimate transactions:",
        int((data["isFraud"] == 0).sum())
    )

    return data


def get_dataset_info(data):
    """
    Display basic dataset information.
    """

    return {
        "rows": data.shape[0],
        "columns": data.shape[1],
        "column_names": list(data.columns),
        "missing_values": data.isnull().sum().to_dict()
    }