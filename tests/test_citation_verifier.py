from src.citation_verifier import verify_citations


def test_valid_citation_is_verified():
    findings = [{"description": "pool saturated", "confidence": "confirmed", "line_ref": "L2: 'Active connections: 50/50'"}]
    result = verify_citations(findings, ["info", "WARN Active connections: 50/50"])
    assert result[0]["verified"] is True


def test_invalid_citation_is_downgraded():
    findings = [{"description": "fabricated", "confidence": "confirmed", "line_ref": "L99: 'not present'"}]
    result = verify_citations(findings, ["actual"])
    assert result[0]["confidence"] == "unverified"
    assert result[0]["verified"] is False


def test_non_confirmed_is_not_verified():
    result = verify_citations([{"confidence": "likely", "line_ref": None}], ["actual"])
    assert result[0]["verified"] is None


def test_missing_confirmed_citation_is_downgraded():
    result = verify_citations([{"confidence": "confirmed", "line_ref": None}], ["actual"])
    assert result[0]["confidence"] == "unverified"
