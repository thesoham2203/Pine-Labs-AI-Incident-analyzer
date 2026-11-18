"""Groq integration with strict JSON parsing and a rule-based fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from prompts.analysis_prompt import SYSTEM_PROMPT
from .citation_verifier import verify_citations

MAX_EVIDENCE_LINES = 200

# Load project-local settings when running outside Streamlit as well. Existing
# process environment variables take precedence over values in the .env file.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _safe_evidence(records: list[Any]) -> str:
    """Bound untrusted log content before it is sent to the model."""
    relevant = [record for record in records if record.level in {"WARN", "ERROR", "FATAL", "CRITICAL"}]
    selected = relevant if len(relevant) <= MAX_EVIDENCE_LINES else relevant[:100] + relevant[-100:]
    return "\n".join(
        f"L{record.line_number}: {''.join(char for char in record.raw if char.isprintable())[:1000]}"
        for record in selected
    )


def _normalise_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("AI response must be a JSON object.")
    root = value.get("root_cause_analysis")
    findings = root.get("findings", []) if isinstance(root, dict) else []
    checks = value.get("diagnostic_checks", [])
    severity = value.get("severity")
    escalation = value.get("escalation")
    return {
        "root_cause_analysis": {"findings": [item for item in findings if isinstance(item, dict)]},
        "severity": {
            "level": severity.get("level") if isinstance(severity, dict) else None,
            "reasoning": str(severity.get("reasoning", "")) if isinstance(severity, dict) else "",
        },
        "incident_summary": str(value.get("incident_summary", "")),
        "diagnostic_checks": sorted([
            item for item in checks
            if isinstance(item, dict)
            and item.get("action")
            and item.get("type") in {"read_only", "owning_team_decision"}
        ], key=lambda item: item["type"] != "read_only") if isinstance(checks, list) else [],
        "escalation": {
            "should_escalate": bool(escalation.get("should_escalate")) if isinstance(escalation, dict) else False,
            "to": str(escalation.get("to", "")) if isinstance(escalation, dict) else "",
            "reason": str(escalation.get("reason", "")) if isinstance(escalation, dict) else "",
        },
        "insufficient_evidence": bool(value.get("insufficient_evidence")),
    }


def _fallback(analysis: dict[str, Any]) -> dict[str, Any]:
    findings = [
        {"description": pattern.replace("_", " ").capitalize() + " pattern detected.",
         "confidence": "confirmed", "line_ref": f"L{lines[0]}"}
        for pattern, lines in analysis.get("pattern_evidence", {}).items() if lines
    ]
    return {
        "root_cause_analysis": {"findings": findings},
        "severity": {"level": None, "reasoning": "Rule-based classification is authoritative."},
        "incident_summary": "Rule-based analysis completed. Configure GROQ_API_KEY for AI-assisted interpretation.",
        "diagnostic_checks": [
            {"action": "Review the highest-frequency error pattern and surrounding log lines.",
             "type": "read_only", "tests_hypothesis": "The dominant pattern contributes to the incident."},
            {"action": "Compare affected service metrics with the incident timeline.",
             "type": "read_only", "tests_hypothesis": "The log failures correlate with user impact."},
        ],
        "escalation": {
            "should_escalate": analysis.get("error_count", 0) > 0,
            "to": "Owning service team",
            "reason": "Errors were detected in the supplied logs.",
        },
        "insufficient_evidence": analysis.get("error_count", 0) < 2,
        "available": False,
        "error": "GROQ_API_KEY is not configured; showing rule-based results only.",
    }


def analyze_with_ai(records: list[Any], analysis: dict[str, Any]) -> dict[str, Any]:
    """Call Groq once when configured, otherwise return a safe fallback."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key.lower() in {"your_key_here", "gsk_your_api_key_here"} or api_key.lower().startswith("gsk_your_"):
        return _fallback(analysis)
    try:
        from groq import Groq
    except ImportError as exc:
        fallback = _fallback(analysis)
        fallback["error"] = f"AI dependency unavailable ({type(exc).__name__}); showing rule-based results only."
        return fallback
    try:
        client = Groq(api_key=api_key)
        prompt = {
            "analysis": {key: value for key, value in analysis.items() if key != "timeline"},
            "evidence_lines": _safe_evidence(records),
            "schema": "Return JSON with root_cause_analysis.findings, severity, incident_summary, diagnostic_checks, escalation, insufficient_evidence.",
        }
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        result = _normalise_result(json.loads(response.choices[0].message.content))
        result["available"] = True
        numbered_lines = [""] * (max((record.line_number for record in records), default=0))
        for record in records:
            numbered_lines[record.line_number - 1] = record.raw
        result["root_cause_analysis"]["findings"] = verify_citations(
            result["root_cause_analysis"]["findings"], numbered_lines
        )
        return result
    except Exception as exc:
        fallback = _fallback(analysis)
        fallback["error"] = f"AI analysis unavailable ({type(exc).__name__}); showing rule-based results only."
        return fallback
