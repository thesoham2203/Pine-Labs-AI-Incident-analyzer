"""Explainable first-pass analysis of parsed logs."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any

from .log_parser import LogRecord

PATTERNS = {
    "timeout": re.compile(r"\btimeout|timed out|slow", re.I),
    "connection_failure": re.compile(r"connection (?:to )?.*(?:failed|refused|dropped|reset)|connection pool|broken pipe", re.I),
    "authentication_failure": re.compile(r"signature|token validation|authentication|jwks|certificate mismatch|401", re.I),
    "server_error": re.compile(r"\b5\d{2}\b|service unavailable|upstream dependency", re.I),
    "application_exception": re.compile(r"exception|stack trace|nullpointer|classnotfound|deadlock", re.I),
    "resource_pressure": re.compile(r"cpu|memory|oom|saturation|active connections|queue", re.I),
}


def _is_error(record: LogRecord) -> bool:
    return record.level in {"ERROR", "FATAL", "CRITICAL"}


def analyze_patterns(records: list[LogRecord]) -> dict[str, Any]:
    """Return counts, rates, timeline, affected paths, and evidence lines."""
    if not records:
        raise ValueError("At least one parsed record is required.")
    errors = [record for record in records if _is_error(record)]
    timed = [record.timestamp for record in records if record.timestamp]
    error_times = [record.timestamp for record in errors if record.timestamp]
    if len(timed) >= 2:
        window_minutes = max((max(timed) - min(timed)).total_seconds() / 60, 1 / 60)
    else:
        window_minutes = max(len(records) / 60, 1 / 60)
    error_rate = len(errors) / window_minutes
    error_services = sorted({record.source for record in errors if record.source != "Unknown"})
    counts = Counter()
    evidence: dict[str, list[int]] = {name: [] for name in PATTERNS}
    pattern_times: dict[str, list] = {name: [] for name in PATTERNS}
    for record in errors:
        for name, pattern in PATTERNS.items():
            if pattern.search(record.message) or pattern.search(record.raw):
                counts[name] += 1
                evidence[name].append(record.line_number)
                if record.timestamp:
                    pattern_times[name].append(record.timestamp)
    timeline = [
        {
            "line_number": record.line_number,
            "timestamp": record.timestamp.isoformat() if record.timestamp else None,
            "level": record.level,
            "source": record.source,
            "message": record.message,
        }
        for record in records
        if record.level in {"WARN", "ERROR", "FATAL", "CRITICAL"}
    ]
    paths = {
        "payment": any(re.search(r"payment|checkout", service, re.I) for service in error_services)
        or any(re.search(r"payment|checkout|payment_db", record.raw, re.I) for record in errors),
        "auth": any(re.search(r"auth|identity|oauth|login", service, re.I) for service in error_services)
        or any(re.search(r"auth|identity|oauth|login", record.raw, re.I) for record in errors),
    }
    first_error = min(error_times) if error_times else None
    last_error = max(error_times) if error_times else None
    duration_minutes = ((last_error - first_error).total_seconds() / 60) if first_error and last_error else 0
    levels = Counter(record.level for record in records)
    pattern_summary = []
    for name, count in counts.most_common():
        timestamps = pattern_times[name]
        pattern_summary.append({
            "pattern": name,
            "count": count,
            "rate_per_minute": round(count / window_minutes, 2),
            "first_seen": min(timestamps).isoformat() if timestamps else None,
            "last_seen": max(timestamps).isoformat() if timestamps else None,
        })
    return {
        "total_lines": len(records),
        "error_count": len(errors),
        "warning_count": sum(record.level == "WARN" for record in records),
        "error_rate_per_minute": round(error_rate, 2),
        "window_minutes": round(window_minutes, 2),
        "error_duration_minutes": round(duration_minutes, 2),
        "levels": dict(levels),
        "error_services": error_services,
        "service_count": len(error_services),
        "paths": paths,
        "cascading": len(error_services) >= 2,
        "pattern_counts": dict(counts),
        "pattern_evidence": {key: value for key, value in evidence.items() if value},
        "pattern_summary": pattern_summary,
        "timeline": timeline,
    }
