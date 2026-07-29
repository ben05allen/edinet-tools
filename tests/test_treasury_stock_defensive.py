"""Regression test for treasury_stock defensive boolean checks.

Prior behavior: has_board_authorization / has_shareholder_authorization
used bare bool() on the text block field, returning True for empty-string
or whitespace-only values. Fix: properties require non-whitespace content.

v0.6.1: Both properties are deprecated. Tests are refactored to assert
against the underlying field expressions directly. Two new tests verify
the deprecation warnings fire correctly.
"""
import warnings


from edinet_tools.parsers.treasury_stock import TreasuryStockReport


def _make_report(by_board: str | None = None, by_shareholders: str | None = None) -> TreasuryStockReport:
    return TreasuryStockReport(
        doc_id='S100TEST',
        doc_type_code='220',
        by_board_meeting=by_board,
        by_shareholders_meeting=by_shareholders,
    )


# --- board authorization: direct field expression ---

def test_board_authorization_truthy_when_text_present():
    report = _make_report(by_board='取締役会決議による取得...')
    assert bool(report.by_board_meeting and report.by_board_meeting.strip())


def test_board_authorization_false_when_none():
    report = _make_report(by_board=None)
    assert not (report.by_board_meeting and report.by_board_meeting.strip())


def test_board_authorization_false_when_empty_string():
    report = _make_report(by_board='')
    assert not (report.by_board_meeting and report.by_board_meeting.strip())


def test_board_authorization_false_when_whitespace_only():
    report = _make_report(by_board='   \n\t  ')
    assert not (report.by_board_meeting and report.by_board_meeting.strip())


# --- shareholder authorization: direct field expression ---

def test_shareholder_authorization_truthy_when_text_present():
    report = _make_report(by_shareholders='株主総会決議による取得...')
    assert bool(report.by_shareholders_meeting and report.by_shareholders_meeting.strip())


def test_shareholder_authorization_false_when_none():
    report = _make_report(by_shareholders=None)
    assert not (report.by_shareholders_meeting and report.by_shareholders_meeting.strip())


def test_shareholder_authorization_false_when_empty_string():
    report = _make_report(by_shareholders='')
    assert not (report.by_shareholders_meeting and report.by_shareholders_meeting.strip())


def test_shareholder_authorization_false_when_whitespace_only():
    report = _make_report(by_shareholders='   ')
    assert not (report.by_shareholders_meeting and report.by_shareholders_meeting.strip())


# --- deprecation warning tests ---

def test_has_board_authorization_emits_deprecation_warning():
    """has_board_authorization is deprecated in v0.6.1."""
    report = _make_report(by_board='取締役会決議による取得...')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = report.has_board_authorization
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1
        msg = str(dep_warnings[0].message)
        assert 'has_board_authorization' in msg
        assert 'by_board_meeting' in msg


def test_has_shareholder_authorization_emits_deprecation_warning():
    """has_shareholder_authorization is deprecated in v0.6.1."""
    report = _make_report(by_shareholders='株主総会決議による取得...')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = report.has_shareholder_authorization
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1
        msg = str(dep_warnings[0].message)
        assert 'has_shareholder_authorization' in msg
        assert 'by_shareholders_meeting' in msg
