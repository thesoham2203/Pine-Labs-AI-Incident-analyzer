"""Parsing and normalization for timestamped and free-form application logs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import re
from typing import Any

TIMESTAMP_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
    r"\s+(?P<level>TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|FATAL|CRITICAL)\b"
    r"(?:\s+(?P<source>[\w.-]+))?\s*[-:]\s*(?P<message>.*)$",
    re.IGNORECASE,
)
LEVEL_RE = re.compile(r"\b(TRACE|DEBUG|INFO|NOTICE|WARN|WARNING|ERROR|FATAL|CRITICAL)\b", re.I)
SERVICE_RE = re.compile(r"\b([A-Za-z][\w.-]*(?:Service|API|Gateway|Processor|Manager|Pool))\b")
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@dataclass(frozen=True)
class LogRecord:
    line_number: int
    raw: str
    timestamp: datetime | None
    level: str
    source: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["timestamp"] = self.timestamp.isoformat() if self.timestamp else None
        return value


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return None


def parse_logs(text: str) -> list[LogRecord]:
    """Parse non-empty log lines while preserving their original line numbers."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Log input must contain at least one non-empty line.")
    cleaned = ANSI_RE.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    records: list[LogRecord] = []
    for line_number, raw_line in enumerate(cleaned.split("\n"), 1):
        raw = raw_line.strip()
        if not raw:
            continue
        match = TIMESTAMP_RE.match(raw)
        if match:
            timestamp = _parse_timestamp(match.group("timestamp"))
            level = match.group("level").upper().replace("WARNING", "WARN")
            source = match.group("source") or "Unknown"
            message = match.group("message").strip()
        else:
            level_match = LEVEL_RE.search(raw)
            level = level_match.group(1).upper().replace("WARNING", "WARN") if level_match else "UNKNOWN"
            source_match = SERVICE_RE.search(raw)
            source = source_match.group(1) if source_match else "Unknown"
            timestamp = None
            message = raw
        records.append(LogRecord(line_number, raw, timestamp, level, source, message))
    if not records:
        raise ValueError("Log input must contain at least one non-empty line.")
    return records
