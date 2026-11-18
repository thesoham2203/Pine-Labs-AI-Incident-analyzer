from datetime import datetime
import pytest

from src.log_parser import parse_logs


def test_timestamped_lines_are_structured():
    records = parse_logs("2026-11-18 10:00:00 ERROR PaymentService - request timed out")
    assert records[0].line_number == 1
    assert records[0].timestamp == datetime(2026, 11, 18, 10, 0)
    assert records[0].source == "PaymentService"
    assert records[0].level == "ERROR"


def test_free_form_lines_fallback():
    records = parse_logs("ERROR PaymentService request failed\n\nINFO recovered")
    assert len(records) == 2
    assert records[0].line_number == 1
    assert records[1].line_number == 3


def test_empty_input_is_rejected():
    with pytest.raises(ValueError):
        parse_logs(" \n ")
