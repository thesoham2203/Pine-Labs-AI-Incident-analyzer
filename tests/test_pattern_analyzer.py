from pathlib import Path

from src.log_parser import parse_logs
from src.pattern_analyzer import analyze_patterns


def load(name):
    return parse_logs((Path(__file__).parents[1] / "sample_logs" / name).read_text())


def test_payment_patterns_and_rate():
    analysis = analyze_patterns(load("payment_api_timeout.log"))
    assert analysis["error_count"] > 0
    assert analysis["error_rate_per_minute"] > 0
    assert analysis["paths"]["payment"]
    assert analysis["cascading"]
    assert analysis["pattern_counts"]["connection_failure"] > 0


def test_healthy_log_has_no_errors():
    analysis = analyze_patterns(load("healthy_system.log"))
    assert analysis["error_count"] == 0
    assert analysis["error_rate_per_minute"] == 0
