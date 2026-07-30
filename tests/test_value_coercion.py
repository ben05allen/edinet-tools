"""Tests for multi-shape value coercion.

Per spec §3.5: handle EDINET's varied null-placeholder shapes:
'－' (full-width minus, U+FF0D), '-' (ASCII), '−' (minus sign U+2212),
'' (empty). All should coerce to None when expecting numeric.
"""

from edinet_tools.parsers.extraction import coerce_int, coerce_numeric_value, parse_int


def test_coerce_numeric_value_handles_dash_placeholders():
    """All dash-shaped placeholders coerce to None."""
    assert coerce_numeric_value("－") is None  # U+FF0D full-width minus
    assert coerce_numeric_value("-") is None
    assert coerce_numeric_value("−") is None  # U+2212 minus sign
    assert coerce_numeric_value("") is None
    assert coerce_numeric_value(None) is None
    assert coerce_numeric_value("   ") is None  # whitespace-only


def test_coerce_numeric_value_passes_through_valid_numerics():
    """Valid numeric strings pass through unchanged."""
    assert coerce_numeric_value("1000") == "1000"
    assert coerce_numeric_value("1000.5") == "1000.5"
    assert coerce_numeric_value("-1000") == "-1000"  # negative number, not placeholder
    assert coerce_numeric_value("1,000,000") == "1,000,000"  # comma-separated


def test_coerce_numeric_value_handles_full_width_digits():
    """Full-width digits convert to half-width."""
    assert coerce_numeric_value("１０００") == "1000"
    assert coerce_numeric_value("１，０００") == "1,000"


def test_coerce_int_with_placeholders():
    """coerce_int returns None for placeholder values."""
    assert coerce_int("－") is None
    assert coerce_int("-") is None
    assert coerce_int("") is None
    assert coerce_int(None) is None


def test_coerce_int_with_valid_input():
    """coerce_int parses numeric strings to int, stripping commas."""
    assert coerce_int("1000") == 1000
    assert coerce_int("1,000,000") == 1000000


def test_coerce_int_with_negative_number():
    """coerce_int correctly handles negative numbers (not placeholders)."""
    assert coerce_int("-1000") == -1000


def test_coerce_int_with_full_width_digits():
    assert coerce_int("１０００") == 1000


# ── U+2212 negative number tests (regression: flaw #1) ─────────────────


def test_coerce_numeric_value_normalizes_u2212_in_negative_numbers():
    """U+2212 (−) in negative numbers must normalize to ASCII minus."""
    assert coerce_numeric_value("\u2212500") == "-500"
    assert coerce_numeric_value("\u2212500000000") == "-500000000"
    assert coerce_numeric_value("\u22120.0967") == "-0.0967"


def test_coerce_int_with_u2212_negative():
    """coerce_int must parse U+2212-prefixed negatives correctly."""
    assert coerce_int("\u2212500") == -500
    assert coerce_int("\u22121000000") == -1000000


def test_coerce_int_with_u2212_still_returns_none_for_bare():
    """Bare U+2212 alone is still a null placeholder."""
    assert coerce_int("\u2212") is None


# ── parse_int rounding tests (regression: flaw #4) ──────────────────────


def test_parse_int_rounds_instead_of_truncating():
    """parse_int must round, not truncate (regression: int(float()) bug)."""
    assert parse_int("99999.7") == 100000
    assert parse_int("99999.3") == 99999
    assert parse_int("2.5") == 2  # Python banker's rounding
    assert parse_int("3.5") == 4
    assert parse_int("-2.5") == -2
    assert parse_int("-3.5") == -4


def test_parse_int_with_u2212_negative():
    """parse_int must handle U+2212 (mathematical minus) in negatives."""
    assert parse_int("\u2212500") == -500
    assert parse_int("\u2212500000000") == -500000000


def test_parse_int_with_u2212_still_returns_none_for_bare():
    """Bare U+2212 alone is still a null placeholder."""
    assert parse_int("\u2212") is None


def test_parse_int_with_u2212_null_markers():
    """All null markers including U+2212 return None."""
    assert parse_int("\uff0d") is None  # U+FF0D full-width minus
    assert parse_int("\u2015") is None  # U+2015 em dash
    assert parse_int("-") is None
    assert parse_int("—") is None  # U+2014 em dash
    assert parse_int("") is None
    assert parse_int(None) is None
