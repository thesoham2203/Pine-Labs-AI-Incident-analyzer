"""Markdown incident report generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

CONFIDENCE_MARKER = {
    "confirmed":  "✅",
    "likely":     "🔶",
    "possible":   "❓",
    "unverified": "⚠️",
}


def _safe(value: str | None, fallback: str = "—") -> str:
    return str(value).strip() if value else fallback


def generate_report(
    analysis: dict[str, Any],
    severity: dict[str, Any],
    ai: dict[str, Any],
) -> str:
    findings = ai.get("root_cause_analysis", {}).get("findings", [])
    checks = ai.get("diagnostic_checks", [])
    escalation = ai.get("escalation", {})
    level = severity["level"]
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines += [
        "# 🚨 Incident Analysis Report",
        "",
        f"> **Generated:** {now}  ",
        f"> **Severity:** {level.upper()}  ",
        f"> **Score:** {severity['score']} / 100  ",
        f"> **Analysis method:** Rule-based deterministic" + (" + Groq AI" if ai.get("available") else " (AI unavailable)"),
        "",
        "---",
        "",
    ]

    # ── Executive summary ──────────────────────────────────────────────────────
    lines += [
        "## Executive Summary",
        "",
        _safe(ai.get("incident_summary"), "No AI summary available. See pattern analysis below."),
        "",
    ]

    if ai.get("insufficient_evidence"):
        lines += [
            "> ⚠️ **Insufficient evidence** — the logs contain too few signals to determine",
            "> a root cause with confidence. Collect more log data before taking action.",
            "",
        ]

    # ── Severity breakdown ─────────────────────────────────────────────────────
    lines += [
        "## Severity Assessment",
        "",
        f"**Level:** {level}  ",
        f"**Deterministic score:** {severity['score']} / 100  ",
        "",
        severity["reason"],
        "",
    ]
    if severity.get("overrides"):
        lines += ["**Override rules applied:**", ""]
        for override in severity["overrides"]:
            lines.append(f"- {override}")
        lines.append("")

    comp = severity.get("components", {})
    lines += [
        "| Component | Points |",
        "|-----------|-------:|",
        f"| Error rate | {comp.get('error_rate', 0)} |",
        f"| Highest log level | {comp.get('level', 0)} |",
        f"| Blast radius (services) | {comp.get('blast_radius', 0)} |",
        f"| Error duration | {comp.get('duration', 0)} |",
        f"| **Total** | **{severity['score']}** |",
        "",
    ]
    if severity.get("ai_disagreement"):
        lines += [
            f"> 💡 Groq suggested **{severity['ai_level']}** severity.",
            "> The displayed level is the deterministic rule-based result.",
            "",
        ]

    # ── Key error patterns ─────────────────────────────────────────────────────
    lines += [
        "## Key Error Patterns",
        "",
        f"**Total log lines parsed:** {analysis['total_lines']}  ",
        f"**Errors:** {analysis['error_count']} · **Warnings:** {analysis['warning_count']}  ",
        f"**Error rate:** {analysis['error_rate_per_minute']:.2f} errors/min over {analysis['window_minutes']:.1f} min window  ",
        f"**Error window duration:** {analysis['error_duration_minutes']:.1f} min  ",
        f"**Affected services:** {', '.join(analysis['error_services']) or 'None identified'}",
        "",
    ]
    if analysis.get("pattern_summary"):
        lines += [
            "| Pattern | Count | Rate /min | First seen | Last seen |",
            "|---------|------:|----------:|-----------|----------|",
        ]
        for item in analysis["pattern_summary"]:
            lines.append(
                f"| {item['pattern'].replace('_', ' ').title()} "
                f"| {item['count']} "
                f"| {item['rate_per_minute']:.2f} "
                f"| {_safe(item.get('first_seen', ''))[:19]} "
                f"| {_safe(item.get('last_seen', ''))[:19]} |"
            )
        lines.append("")

    # ── Timeline ───────────────────────────────────────────────────────────────
    timeline = analysis.get("timeline", [])
    if timeline:
        lines += [
            "## Event Timeline",
            "",
            "| Line | Timestamp | Level | Service | Message |",
            "|-----:|-----------|-------|---------|---------|",
        ]
        for event in timeline[:60]:
            ts = str(event.get("timestamp") or "—")[:19]
            msg = str(event.get("message") or "")[:120].replace("|", "\\|")
            lines.append(
                f"| {event['line_number']} "
                f"| {ts} "
                f"| {event['level']} "
                f"| {event['source']} "
                f"| {msg} |"
            )
        if len(timeline) > 60:
            lines.append(f"\n*…and {len(timeline) - 60} more events (not shown for brevity)*")
        lines.append("")

    # ── Root cause analysis ────────────────────────────────────────────────────
    lines += ["## Root Cause Analysis", ""]
    if findings:
        for finding in findings:
            conf = finding.get("confidence", "unknown")
            marker = CONFIDENCE_MARKER.get(conf, "❓")
            verified = finding.get("verified")
            if conf == "confirmed" and verified is False:
                marker = CONFIDENCE_MARKER["unverified"]
                conf = "unverified"
            line_ref = f" *(citation: {finding['line_ref']})*" if finding.get("line_ref") else ""
            lines.append(f"- {marker} **{conf.title()}:** {finding.get('description', '')}{line_ref}")
        lines.append("")
    else:
        lines += ["*No root cause findings returned.*", ""]

    # ── Diagnostic checks ──────────────────────────────────────────────────────
    ro_checks = [c for c in checks if c.get("type") == "read_only"]
    td_checks = [c for c in checks if c.get("type") != "read_only"]

    lines += ["## Diagnostic Checks", ""]
    if ro_checks:
        lines += ["### 🟢 Safe to run (read-only)", ""]
        for i, check in enumerate(ro_checks, 1):
            lines.append(f"{i}. **{check.get('action', '')}**")
            if check.get("tests_hypothesis"):
                lines.append(f"   - *Tests:* {check['tests_hypothesis']}")
        lines.append("")
    if td_checks:
        lines += ["### 🟠 Requires owning team decision", ""]
        for i, check in enumerate(td_checks, 1):
            lines.append(f"{i}. **{check.get('action', '')}**")
            if check.get("tests_hypothesis"):
                lines.append(f"   - *Tests:* {check['tests_hypothesis']}")
        lines.append("")

    # ── Escalation ─────────────────────────────────────────────────────────────
    lines += ["## Escalation", ""]
    if escalation.get("should_escalate"):
        lines += [
            f"⚠️ **Escalate to:** {_safe(escalation.get('to'))}  ",
            f"**Reason:** {_safe(escalation.get('reason'))}",
            "",
        ]
    else:
        lines += ["✅ No escalation required at this time.", ""]

    # ── Disclaimer ─────────────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "> **Potential Remediation** — Any restart, rollback, or configuration change must be",
        "> confirmed by the owning team after completing the diagnostic checks above.",
        "> This report uses simulated log data only.",
        "",
    ]

    return "\n".join(lines)
