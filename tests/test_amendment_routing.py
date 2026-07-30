"""Tests that amendment doc types route to the correct base parser."""

import io
import zipfile
from unittest.mock import MagicMock

import pytest

from edinet_tools.parsers import parse
from edinet_tools.parsers.generic import RawReport


def _make_minimal_zip() -> bytes:
    """Build a minimal valid EDINET-shaped ZIP containing a single CSV row.

    A real (non-empty) ZIP makes parsers walk the real parse body
    (extract_csv_from_zip → field extraction → categorize_elements) rather
    than short-circuiting on the empty-csv_files branch.
    """
    # 9-column EDINET CSV row: element_id, label, context_id, year, consol,
    # period, unit_id, unit, value
    row = "jpdei_cor:EDINETCodeDEI\tlabel\tFilingDateInstant\t0\t連結\t期間\t\t\tE12345"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("XBRL_TO_CSV/test.csv", row.encode("utf-16le"))
    return buf.getvalue()


def _make_doc(code: str) -> MagicMock:
    doc = MagicMock()
    doc.doc_type_code = code
    doc.doc_id = f"TEST_{code}"
    doc.filer_edinet_code = ""
    doc.fetch.return_value = _make_minimal_zip()
    return doc


AMENDMENT_ROUTES = [
    ("130", "120"),  # Securities Report Amendment -> Securities Report
    ("150", "140"),  # Quarterly Report Amendment -> Quarterly Report
    ("170", "160"),  # Semi-Annual Report Amendment -> Semi-Annual Report
    ("190", "180"),  # Extraordinary Report Amendment -> Extraordinary Report
    ("360", "350"),  # Large Shareholding Amendment -> Large Shareholding Report
]


@pytest.mark.parametrize("amendment_code,base_code", AMENDMENT_ROUTES)
def test_amendment_does_not_fall_through_to_raw(amendment_code, base_code):
    """Amendment doc types should NOT fall through to RawReport/parse_raw."""
    doc = _make_doc(amendment_code)
    result = parse(doc)
    assert not isinstance(result, RawReport), (
        f"Doc type {amendment_code} fell through to RawReport instead of routing to base parser"
    )
    # The CSV row we fed in has the DEI EDINET code 'E12345' — proves
    # the parse body actually ran rather than short-circuiting on empty input.
    assert result.raw_fields.get("jpdei_cor:EDINETCodeDEI") == "E12345", (
        f"Doc type {amendment_code}: parse body did not consume the input CSV row"
    )


def test_existing_amendment_routes_still_work():
    """Verify pre-existing amendment routes (230, 250) are unchanged."""
    for code in ["230", "250"]:
        doc = _make_doc(code)
        result = parse(doc)
        assert not isinstance(result, RawReport)
        assert result.raw_fields.get("jpdei_cor:EDINETCodeDEI") == "E12345", (
            f"Doc type {code}: parse body did not consume the input CSV row"
        )
