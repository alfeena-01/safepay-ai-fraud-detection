from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.extensions.member3.app.detectors.account_takeover_detector import detect_account_takeover
from app.extensions.member3.app.detectors.device_fingerprinting import check_device
from app.extensions.member3.app.detectors.duplicate_transaction_detector import detect_duplicate_transaction
from app.extensions.member3.app.detectors.fraud_pattern_recognition import detect_fraud_patterns
from app.extensions.member3.app.detectors.phishing_url_detector import detect_phishing_url
from app.extensions.member3.app.detectors.real_time_risk_engine import calculate_risk_score
from app.extensions.member3.app.detectors.suspicious_login_detector import detect_suspicious_login

router = APIRouter(prefix="/member3", tags=["Member 3 Security Intelligence"])

class DeviceInfo(BaseModel):
    device_type: str = "Unknown"
    os: str = "Unknown"
    browser: str = "Unknown"
    screen_resolution: str = "Unknown"

class SecurityAssessmentRequest(BaseModel):
    transaction_id: str = Field(default="DEMO-TXN", max_length=100)
    account_id: str = Field(default="DEMO-ACCOUNT", max_length=100)
    amount: float = Field(default=0, ge=0)
    merchant: str = Field(default="Unknown", max_length=200)
    timestamp: str = Field(default="Unknown", max_length=100)
    url: str = Field(default="https://example.com", max_length=2048)
    failed_login_attempts: int = Field(default=0, ge=0, le=1000)
    password_reset_attempts: int = Field(default=0, ge=0, le=1000)
    new_device: bool = False
    unusual_time: bool = False
    unusual_location: bool = False
    profile_changed: bool = False
    device: DeviceInfo = Field(default_factory=DeviceInfo)
    previous_transactions: list[dict] = Field(default_factory=list, max_length=100)
    known_devices: list[str] = Field(default_factory=list, max_length=100)

@router.post("/assess")
def assess_security(request: SecurityAssessmentRequest):
    phishing = detect_phishing_url(request.url)
    takeover = detect_account_takeover(
        failed_login_attempts=request.failed_login_attempts,
        new_device=request.new_device,
        password_reset_attempts=request.password_reset_attempts,
        profile_changed=request.profile_changed,
        unusual_location=request.unusual_location,
    )
    login = detect_suspicious_login(
        new_device=request.new_device,
        unusual_time=request.unusual_time,
        unusual_location=request.unusual_location,
        failed_attempts=request.failed_login_attempts,
    )
    current = {
        "account_id": request.account_id,
        "amount": request.amount,
        "merchant": request.merchant,
        "timestamp": request.timestamp,
    }
    duplicate = detect_duplicate_transaction(current, request.previous_transactions)
    duplicate_risk = 100 if duplicate.get("is_duplicate") else 0
    pattern_input = request.previous_transactions + [{
        "amount": request.amount, "merchant": request.merchant
    }]
    patterns = detect_fraud_patterns(pattern_input)
    device = check_device(request.device.model_dump(), request.known_devices)
    risk = calculate_risk_score(
        phishing_risk=phishing["risk_score"],
        account_takeover_risk=takeover["risk_score"],
        suspicious_login_risk=login["risk_score"],
        duplicate_transaction_risk=duplicate_risk,
        fraud_pattern_risk=patterns["risk_score"],
        device_fingerprint_risk=device["risk_score"],
    )
    return {
        "transaction_id": request.transaction_id,
        "overall_assessment": risk,
        "detectors": {
            "phishing_url": phishing,
            "account_takeover": takeover,
            "suspicious_login": login,
            "duplicate_transaction": duplicate,
            "fraud_patterns": patterns,
            "device_fingerprinting": device,
        },
        "disclaimer": "Rule-based educational decision support; review the evidence. A score is not proof of fraud."
    }
