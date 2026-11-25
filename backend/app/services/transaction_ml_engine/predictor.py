def predict_transaction(model, transaction):
    """
    Predict whether a transaction is fraudulent.
    """

    # Get prediction
    prediction = model.predict(transaction)[0]

    # Get fraud probability
    probabilities = model.predict_proba(transaction)[0]

    fraud_probability = probabilities[
        list(model.classes_).index(1)
    ]

    # Identify transaction status
    if prediction == 1:
        status = "Fraud"
    else:
        status = "Legitimate"

    return {
        "prediction": int(prediction),
        "status": status,
        "fraud_probability": round(
            float(fraud_probability) * 100, 2
        )
    }