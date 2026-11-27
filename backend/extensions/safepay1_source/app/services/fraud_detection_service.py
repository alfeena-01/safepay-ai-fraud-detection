from app.services.transaction_ml_engine.data_loader import (
    load_transaction_data,
    validate_transaction_data
)

from app.services.transaction_ml_engine.preprocessing import (
    clean_transaction_data,
    separate_features_and_target
)

from app.services.transaction_ml_engine.feature_engineering import (
    create_transaction_features
)

from app.services.transaction_ml_engine.model import (
    train_fraud_model,
    predict_fraud
)

from app.services.transaction_ml_engine.evaluator import (
    evaluate_model
)


def train_fraud_detection_model(file_path):

    # Load dataset
    data = load_transaction_data(file_path)

    # Validate dataset
    validate_transaction_data(data)

    # Clean dataset
    data = clean_transaction_data(data)

    # Separate features and target
    X, y = separate_features_and_target(data)

    # Create additional features
    X = create_transaction_features(X)

    # Train machine learning model
    model, X_test, y_test = train_fraud_model(X, y)

    # Evaluate model
    results = evaluate_model(model, X_test, y_test)

    return model, results


def check_transaction(model, transaction):

    transaction = create_transaction_features(transaction)

    prediction = predict_fraud(model, transaction)

    if prediction[0] == 1:
        return "Fraudulent Transaction"

    return "Legitimate Transaction"