from datetime import datetime

# Temporary transaction storage
transactions = []


def add_transaction(user_id, transaction_id, amount, transaction_type, status):

    transaction = {
        "user_id": user_id,
        "transaction_id": transaction_id,
        "amount": amount,
        "type": transaction_type,
        "status": status,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    transactions.append(transaction)

    return transaction


def get_transaction_history(user_id):

    return [
        transaction
        for transaction in transactions
        if transaction["user_id"] == user_id
    ]