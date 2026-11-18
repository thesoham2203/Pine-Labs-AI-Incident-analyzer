"""Verify evidence citations returned by the language model."""

from __future__ import annotations

import re
from typing import Any


def verify_citations(findings: list[dict[str, Any]], log_lines: list[str]) -> list[dict[str, Any]]:
    """Downgrade confirmed findings whose line reference cannot be verified."""
    result = []
    for original in findings:
        finding = dict(original)
        if finding.get("confidence") != "confirmed":
            finding["verified"] = None
            result.append(finding)
            continue
        reference = str(finding.get("line_ref") or "")
        match = re.search(r"\bL(\d+)\b", reference, re.I)
        quote_match = re.search(r"""['"](.+?)['"]""", reference)
        line_number = int(match.group(1)) if match else None
        valid_line = line_number is not None and 1 <= line_number <= len(log_lines)
        quote = quote_match.group(1).strip() if quote_match else ""
        valid_quote = not quote or (valid_line and quote.lower() in log_lines[line_number - 1].lower())
        finding["verified"] = bool(valid_line and valid_quote)
        if not finding["verified"]:
            finding["confidence"] = "unverified"
        result.append(finding)
    return result
