from app.detectors.device_fingerprinting import (
    generate_device_fingerprint,
    check_device
)


def test_fingerprint():
    device = {
        "device_type": "Laptop",
        "os": "Windows 11",
        "browser": "Edge",
        "screen_resolution": "1920x1080"
    }

    fingerprint = generate_device_fingerprint(device)

    assert fingerprint == "Laptop|Windows 11|Edge|1920x1080"


def test_known_device():
    device = {
        "device_type": "Mobile",
        "os": "Android",
        "browser": "Chrome",
        "screen_resolution": "1080x2400"
    }

    known_devices = ["Mobile|Android|Chrome|1080x2400"]

    result = check_device(device, known_devices)

    assert result["status"] == "Known Device"
    assert result["risk_score"] == 10


def test_new_device():
    device = {
        "device_type": "Laptop",
        "os": "Windows 11",
        "browser": "Edge",
        "screen_resolution": "1920x1080"
    }

    known_devices = ["Mobile|Android|Chrome|1080x2400"]

    result = check_device(device, known_devices)

    assert result["status"] == "New Device"
    assert result["risk_score"] == 60


if __name__ == "__main__":
    test_fingerprint()
    test_known_device()
    test_new_device()

    print("ALL DEVICE FINGERPRINTING TESTS PASSED!")