def get_voice_support_response(message):

    message = message.lower()

    if "fraud" in message or "scam" in message:
        return "If you suspect fraud, please block your transaction and contact SafePay support."

    elif "transaction" in message or "payment" in message:
        return "Please check your transaction history to view your payment details."

    elif "emergency" in message or "help" in message:
        return "Please use the Emergency Help button to request assistance."

    elif "account" in message:
        return "Please verify your account details and contact SafePay support if needed."

    else:
        return "Thank you for contacting SafePay. How can we help you?"