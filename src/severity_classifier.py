"""Deterministic, rate-based severity classification."""

from __future__ import annotations

from typing import Any


def _level_points(levels: dict[str, int]) -> int:
    if levels.get("FATAL", 0) or levels.get("CRITICAL", 0):
        return 25
    if levels.get("ERROR", 0):
        return 15
    if levels.get("WARN", 0):
        return 5
    return 0


def classify_severity(analysis: dict[str, Any], ai_level: str | None = None) -> dict[str, Any]:
    """Classify severity; AI may be reported but never overrides deterministic rules."""
    errors = analysis.get("error_count", 0)
    rate = float(analysis.get("error_rate_per_minute", 0))
    service_count = analysis.get("service_count", 0)
    duration = float(analysis.get("error_duration_minutes", 0))
    rate_points = 0 if not errors else 8 if rate <= 1 else 15 if rate <= 5 else 25 if rate <= 15 else 35
    blast_points = 25 if service_count >= 3 else 15 if service_count == 2 else 8 if service_count == 1 else 0
    duration_points = 0 if not errors else 15 if duration > 30 else 10 if duration >= 10 else 6 if duration >= 2 else 3
    points = rate_points + _level_points(analysis.get("levels", {})) + blast_points + duration_points
    if points == 0:
        level = "None"
    elif points <= 24:
        level = "Low"
    elif points <= 49:
        level = "Medium"
    elif points <= 74:
        level = "High"
    else:
        level = "Critical"
    paths = analysis.get("paths", {})
    overrides: list[str] = []
    if duration > 2 and paths.get("payment"):
        if level not in {"High", "Critical"}:
            level = "High"
        overrides.append("Sustained payment-path errors set a High floor.")
    if duration > 2 and paths.get("auth"):
        if level in {"None", "Low", "Medium"}:
            level = "High"
        overrides.append("Sustained authentication-path errors set a High floor.")
    # Only apply the DB-connection floor when an explicitly named DB/data service is affected,
    # not for generic connection_failure on application services like InventoryService.
    db_services = {s for s in analysis.get("error_services", []) if any(
        kw in s.lower() for kw in ("database", "db", "postgres", "mysql", "redis", "mongo", "data")
    )}
    if duration > 10 and analysis.get("pattern_counts", {}).get("connection_failure", 0) >= 3 and db_services:
        if level in {"None", "Low", "Medium"}:
            level = "High"
        overrides.append("Sustained repeated database connection failures set a High floor.")
    if paths.get("payment") and analysis.get("cascading"):
        level = "Critical"
        overrides.append("Payment-path cascading across multiple services sets a Critical floor.")
    reason = (
        f"{errors} errors at {rate:.2f}/min across {service_count} service(s), "
        f"with an error window of {duration:.2f} minute(s), produced a base score of {points}/100."
    )
    if overrides:
        reason += " " + " ".join(overrides)
    return {
        "level": level,
        "score": points,
        "reason": reason,
        "components": {"error_rate": rate_points, "level": _level_points(analysis.get("levels", {})), "blast_radius": blast_points, "duration": duration_points},
        "ai_level": ai_level,
        "ai_disagreement": bool(ai_level and ai_level.title() != level),
        "overrides": overrides,
    }
