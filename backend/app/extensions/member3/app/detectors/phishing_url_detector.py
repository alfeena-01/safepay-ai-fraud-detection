from urllib.parse import urlparse
import re


def detect_phishing_url(url):
    risk_score = 0
    reasons = []

    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    # Check HTTPS
    if parsed.scheme != "https":
        risk_score += 15
        reasons.append("URL does not use HTTPS")

    # Check IP address instead of domain name
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
        risk_score += 25
        reasons.append("URL uses an IP address")

    # Check suspicious keywords
    keywords = [
        "login", "verify", "secure", "update",
        "bank", "wallet", "password", "payment"
    ]

    for keyword in keywords:
        if keyword in url.lower():
            risk_score += 5
            reasons.append(f"Suspicious keyword: {keyword}")

    # Check URL length
    if len(url) > 75:
        risk_score += 15
        reasons.append("URL is unusually long")

    # Check '@' symbol
    if "@" in url:
        risk_score += 20
        reasons.append("URL contains @ symbol")

    # Check excessive subdomains
    if hostname.count(".") >= 3:
        risk_score += 15
        reasons.append("URL has excessive subdomains")

    risk_score = min(risk_score, 100)

    if risk_score >= 50:
        status = "Suspicious"
    elif risk_score >= 25:
        status = "Potential Risk"
    else:
        status = "Low Risk"

    return {
        "url": url,
        "risk_score": risk_score,
        "status": status,
        "reasons": reasons
    }


if __name__ == "__main__":
    test_url = "http://secure-login-verify-example.com"

    result = detect_phishing_url(test_url)

    print("\n===== PHISHING URL ANALYSIS =====")
    print("URL:", result["url"])
    print("Risk Score:", result["risk_score"])
    print("Status:", result["status"])
    print("Reasons:", result["reasons"])