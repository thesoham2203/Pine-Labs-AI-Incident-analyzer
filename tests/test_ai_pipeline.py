from pathlib import Path

from src.ai_analyzer import analyze_with_ai
from src.log_parser import parse_logs
from src.pattern_analyzer import analyze_patterns
from src.report_generator import generate_report
from src.severity_classifier import classify_severity


def test_fallback_pipeline_covers_every_sample(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    for path in (Path(__file__).parents[1] / "sample_logs").glob("*.log"):
        records = parse_logs(path.read_text())
        analysis = analyze_patterns(records)
        ai = analyze_with_ai(records, analysis)
        severity = classify_severity(analysis, ai["severity"]["level"])
        report = generate_report(analysis, severity, ai)
        assert ai["available"] is False
        assert "## Key Error Patterns" in report
        assert "## Diagnostic Checks" in report
