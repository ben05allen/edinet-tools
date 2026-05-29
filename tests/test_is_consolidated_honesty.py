"""Regression test for is_consolidated honest-unknowns fix.

Prior bug: is_consolidated defaulted to True when the
WhetherConsolidatedFinancialStatementsArePreparedDEI element was missing
from the filing. Per facts-not-judgments discipline, missing data should
return None (unknown), not silently True.
"""
from edinet_tools.parsers.quarterly import parse_quarterly_report


def _csv_files_without_consolidated_dei():
    """Synthetic Doc 140 with no WhetherConsolidated...DEI field."""
    return [{
        'filename': 'corp.csv',
        'data': [
            {'要素ID': '要素ID', '項目名': '項目名', 'コンテキストID': 'コンテキストID',
             '相対年度': '', '連結・個別': '', '期間・時点': '', 'ユニットID': '', '単位': '', '値': ''},
            {'要素ID': 'jpdei_cor:EDINETCodeDEI', 'コンテキストID': 'FilingDateInstant', '値': 'E01234'},
            {'要素ID': 'jpcrp_cor:NetSales', 'コンテキストID': 'CurrentYearDuration', 'ユニットID': 'JPY', '値': '1000000000'},
            # No jpdei_cor:WhetherConsolidatedFinancialStatementsArePreparedDEI
        ],
    }]


def _csv_files_with_consolidated_true():
    return [{
        'filename': 'corp.csv',
        'data': [
            {'要素ID': '要素ID', '項目名': '項目名', 'コンテキストID': 'コンテキストID',
             '相対年度': '', '連結・個別': '', '期間・時点': '', 'ユニットID': '', '単位': '', '値': ''},
            {'要素ID': 'jpdei_cor:WhetherConsolidatedFinancialStatementsArePreparedDEI',
             'コンテキストID': 'FilingDateInstant', '値': 'true'},
            {'要素ID': 'jpcrp_cor:NetSales', 'コンテキストID': 'CurrentYearDuration', '値': '1000000000'},
        ],
    }]


def _csv_files_with_consolidated_false():
    return [{
        'filename': 'corp.csv',
        'data': [
            {'要素ID': '要素ID', '項目名': '項目名', 'コンテキストID': 'コンテキストID',
             '相対年度': '', '連結・個別': '', '期間・時点': '', 'ユニットID': '', '単位': '', '値': ''},
            {'要素ID': 'jpdei_cor:WhetherConsolidatedFinancialStatementsArePreparedDEI',
             'コンテキストID': 'FilingDateInstant', '値': 'false'},
        ],
    }]


def test_is_consolidated_is_None_when_dei_missing():
    """Per facts-not-judgments: missing data should return None, not silently True."""
    report = parse_quarterly_report(
        csv_files=_csv_files_without_consolidated_dei(),
        doc_id='S100TEST',
        doc_type_code='140',
    )
    assert report.is_consolidated is None


def test_is_consolidated_is_True_when_dei_says_true():
    report = parse_quarterly_report(
        csv_files=_csv_files_with_consolidated_true(),
        doc_id='S100TEST',
        doc_type_code='140',
    )
    assert report.is_consolidated is True


def test_is_consolidated_is_False_when_dei_says_false():
    report = parse_quarterly_report(
        csv_files=_csv_files_with_consolidated_false(),
        doc_id='S100TEST',
        doc_type_code='140',
    )
    assert report.is_consolidated is False
