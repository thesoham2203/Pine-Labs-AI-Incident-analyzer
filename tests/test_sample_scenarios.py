from pathlib import Path

import pytest

from src.log_parser import parse_logs
from src.pattern_analyzer import analyze_patterns
from src.severity_classifier import classify_severity


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("payment_api_timeout.log", "Critical"),
        ("database_connection.log", "High"),
        ("auth_service_failure.log", "High"),
        ("post_deploy_spike.log", "Medium"),
        ("ambiguous_thin.log", "Low"),
        ("mixed_incident.log", "Medium"),
        ("healthy_system.log", "None"),
    ],
)
def test_sample_scenario_severity_matches_plan(name, expected):
    text = (Path(__file__).parents[1] / "sample_logs" / name).read_text()
    analysis = analyze_patterns(parse_logs(text))
    assert classify_severity(analysis)["level"] == expected
