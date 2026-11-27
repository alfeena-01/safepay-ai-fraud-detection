from datetime import datetime


def generate_fraud_alert(prediction, transaction_id=None, amount=None):

    if prediction == "Fraudulent Transaction" or prediction == 1:

        alert = {
            "alert_status": "WARNING",
            "message": "Suspicious transaction detected!",
            "transaction_id": transaction_id,
            "amount": amount,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "Please verify this transaction immediately."
        }

        return alert

    else:
        return {
            "alert_status": "SAFE",
            "message": "No fraud detected. Transaction appears safe."
        }