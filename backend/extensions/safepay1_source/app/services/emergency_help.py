from datetime import datetime


def create_emergency_request(user_id, message="Emergency help requested"):

    request = {
        "user_id": user_id,
        "message": message,
        "status": "Emergency Request Received",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "priority": "HIGH"
    }

    return request