
def generate_device_fingerprint(current_device):
    device_type = current_device.get("device_type", "")
    os_name = current_device.get("os", "")
    browser = current_device.get("browser", "")
    screen_resolution = current_device.get("screen_resolution", "")

    fingerprint = (
        f"{device_type}|{os_name}|{browser}|{screen_resolution}"
    )

    return fingerprint


def check_device(current_device, known_devices):

    fingerprint = generate_device_fingerprint(current_device)

    if fingerprint in known_devices:
        status = "Known Device"
        risk_score = 10
        message = "Recognized device"
    else:
        status = "New Device"
        risk_score = 60
        message = "New or unrecognized device detected"

    return {
        "fingerprint": fingerprint,
        "status": status,
        "device_status": status,
        "risk_score": risk_score,
        "message": message
    }
