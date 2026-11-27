
import streamlit as st
import pandas as pd

from app.detectors.phishing_url_detector import detect_phishing_url
from app.detectors.account_takeover_detector import detect_account_takeover
from app.detectors.suspicious_login_detector import detect_suspicious_login
from app.detectors.duplicate_transaction_detector import detect_duplicate_transaction
from app.detectors.real_time_risk_engine import calculate_risk_score
from app.detectors.fraud_pattern_recognition import detect_fraud_patterns
from app.detectors.device_fingerprinting import check_device


st.set_page_config(
    page_title="Fraud Investigation Dashboard",
    layout="wide"
)

st.title("Fraud Investigation Dashboard")
st.write("AI-Assisted Transaction Risk Investigation System")

st.info(
    "Educational demonstration. Risk scores are rule-based "
    "and are not validated real-world fraud predictions."
)

st.header("Transaction Details")

transaction_id = st.text_input("Transaction ID", "TXN-1001")
account_id = st.text_input("Account ID", "ACC-1001")
amount = st.number_input("Transaction Amount", min_value=0.0, value=5000.0)
merchant = st.text_input("Merchant", "ABC Store")
timestamp = st.text_input("Timestamp", "2026-11-26 13:00")
url = st.text_input("URL", "https://example.com")

st.header("Account Security")

failed_login_attempts = st.number_input(
    "Failed Login Attempts", min_value=0, value=0
)

password_reset_attempts = st.number_input(
    "Password Reset Attempts", min_value=0, value=0
)

new_device = st.checkbox("New Device")
unusual_time = st.checkbox("Unusual Time")
unusual_location = st.checkbox("Unusual Location")
profile_change = st.checkbox("Profile Change")

st.header("Device Details")

device_type = st.selectbox(
    "Device Type", ["Laptop", "Mobile", "Tablet", "Desktop"]
)

operating_system = st.selectbox(
    "Operating System", ["Windows", "Android", "iOS", "Linux", "macOS"]
)

browser = st.selectbox(
    "Browser", ["Chrome", "Edge", "Firefox", "Safari", "Other"]
)

screen_resolution = st.text_input(
    "Screen Resolution", "1920x1080"
)

st.warning(
    "Duplicate detection uses previous transaction records. "
    "This demonstration starts with an empty history."
)

st.warning(
    "Fraud pattern recognition uses demonstration data, "
    "not a real transaction history."
)

if st.button("Investigate Transaction", type="primary"):

    # 1. Phishing URL Detection
    phishing = detect_phishing_url(url)

    # 2. Account Takeover Detection
    account_takeover = detect_account_takeover(
        failed_login_attempts=failed_login_attempts,
        new_device=new_device,
        password_reset_attempts=password_reset_attempts,
        unusual_location=unusual_location,
        profile_changed=profile_change
    )

    # 3. Suspicious Login Detection
    suspicious_login = detect_suspicious_login(
        new_device=new_device,
        unusual_time=unusual_time,
        unusual_location=unusual_location,
        failed_attempts=failed_login_attempts
    )

    # 4. Duplicate Transaction Detection
    current_transaction = {
        "account_id": account_id,
        "amount": amount,
        "merchant": merchant,
        "timestamp": timestamp
    }

    previous_transactions = []

    duplicate = detect_duplicate_transaction(
        current_transaction,
        previous_transactions
    )

    duplicate_risk = (
        100 if duplicate.get("is_duplicate", False) else 0
    )

    # 5. Fraud Pattern Recognition
    demo_transactions = [
        {"amount": 500, "merchant": "ABC"},
        {"amount": 600, "merchant": "ABC"},
        {"amount": amount, "merchant": merchant},
        {"amount": amount * 2, "merchant": merchant}
    ]

    patterns = detect_fraud_patterns(demo_transactions)

    # 6. Device Fingerprinting
    current_device = {
        "device_type": device_type,
        "os": operating_system,
        "browser": browser,
        "screen_resolution": screen_resolution
    }

    device_result = check_device(
        current_device,
        known_devices=[]
    )

    # 7. Overall Risk Calculation
    risk = calculate_risk_score(
        phishing_risk=phishing["risk_score"],
        account_takeover_risk=account_takeover["risk_score"],
        suspicious_login_risk=suspicious_login["risk_score"],
        duplicate_transaction_risk=duplicate_risk,
        fraud_pattern_risk=patterns["risk_score"],
        device_fingerprint_risk=device_result["risk_score"]
    )

    st.divider()
    st.header("Investigation Results")

    st.subheader("Transaction Summary")

    st.write("Transaction ID:", transaction_id)
    st.write("Account ID:", account_id)
    st.write("Amount:", f"₹{amount:,.2f}")
    st.write("Merchant:", merchant)

    st.subheader("Overall Risk")

    st.metric(
        "Risk Score",
        f'{risk["risk_score"]}/100'
    )

    st.metric(
        "Risk Level",
        risk["risk_level"]
    )

    st.progress(
        min(max(int(risk["risk_score"]), 0), 100)
    )

    st.subheader("Risk Components")

    components = risk["risk_components"]

    component_data = pd.DataFrame(
        list(components.items()),
        columns=["Component", "Score"]
    )

    st.dataframe(
        component_data,
        use_container_width=True
    )

    st.subheader("Individual Detector Results")

    st.write("Phishing URL:", phishing)
    st.write("Account Takeover:", account_takeover)
    st.write("Suspicious Login:", suspicious_login)
    st.write("Duplicate Transaction:", duplicate)
    st.write("Fraud Pattern Recognition:", patterns)
    st.write("Device Fingerprinting:", device_result)

    st.subheader("Risk Component Chart")

    st.bar_chart(
        component_data.set_index("Component")
    )

    st.success("Investigation completed successfully.")
