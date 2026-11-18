from src.severity_classifier import classify_severity


def test_healthy_logs_are_none():
    result = classify_severity({"error_count": 0, "error_rate_per_minute": 0, "service_count": 0, "error_duration_minutes": 0, "levels": {}, "paths": {}})
    assert result["level"] == "None"
    assert result["score"] == 0


def test_payment_cascade_is_critical():
    result = classify_severity({
        "error_count": 5, "error_rate_per_minute": 1.67, "service_count": 2,
        "error_duration_minutes": 3, "levels": {"ERROR": 5}, "paths": {"payment": True},
        "cascading": True,
    })
    assert result["level"] == "Critical"
    assert result["overrides"]


def test_auth_path_has_high_floor():
    result = classify_severity({
        "error_count": 2, "error_rate_per_minute": 0.5, "service_count": 1,
        "error_duration_minutes": 3, "levels": {"ERROR": 2}, "paths": {"auth": True},
    })
    assert result["level"] == "High"
