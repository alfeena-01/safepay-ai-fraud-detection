TRANSLATIONS = {
    "en": {
        "welcome": "Welcome to SafePay",
        "fraud_alert": "Warning! Suspicious transaction detected.",
        "safe_transaction": "Your transaction is safe.",
        "emergency": "Emergency help requested successfully."
    },

    "ml": {
        "welcome": "സേഫ്പേയിലേക്ക് സ്വാഗതം",
        "fraud_alert": "മുന്നറിയിപ്പ്! സംശയാസ്പദമായ ഇടപാട് കണ്ടെത്തി.",
        "safe_transaction": "നിങ്ങളുടെ ഇടപാട് സുരക്ഷിതമാണ്.",
        "emergency": "അടിയന്തര സഹായ അഭ്യർത്ഥന വിജയകരമായി ലഭിച്ചു."
    },

    "hi": {
        "welcome": "सेफपे में आपका स्वागत है",
        "fraud_alert": "चेतावनी! संदिग्ध लेनदेन का पता चला।",
        "safe_transaction": "आपका लेनदेन सुरक्षित है।",
        "emergency": "आपातकालीन सहायता अनुरोध सफलतापूर्वक प्राप्त हुआ।"
    }
}


def get_message(language, message_key):

    language = language.lower()

    if language not in TRANSLATIONS:
        language = "en"

    return TRANSLATIONS[language].get(
        message_key,
        "Message not available"
    )


def get_supported_languages():

    return {
        "en": "English",
        "ml": "Malayalam",
        "hi": "Hindi"
    }