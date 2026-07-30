"""Tests for multi-shape value coercion.

Per spec §3.5: handle EDINET's varied null-placeholder shapes:
'－' (full-width minus, U+FF0D), '-' (ASCII), '−' (minus sign U+2212),
'' (empty). All should coerce to None when expecting numeric.
"""

from edinet_tools.parsers.extraction import coerce_numeric_value, coerce_int


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
