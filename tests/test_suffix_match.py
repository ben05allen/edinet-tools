"""Tests for suffix-tolerant element matching.

Per spec §3.5: match by element-name stem to handle:
- Per-filer custom-element namespaces (jpcrp030000-asr_<EDINET>-000:Foo)
- Industry suffix variants (FooINS, FooBNK)
- Canonical-name variants (Foo, FooLoss)
"""
from edinet_tools.parsers.extraction import match_element_by_suffix


def _csv_files_with_custom_namespaces():
    return [{
        'filename': 'test.csv',
        'data': [
            {'要素ID': '要素ID', '項目名': '項目名', 'コンテキストID': 'コンテキストID',
             '相対年度': '', '連結・個別': '', '期間・時点': '', 'ユニットID': '', '単位': '', '値': ''},
            # Standard namespace
            {'要素ID': 'jpcrp_cor:NetSales', 'コンテキストID': 'CurrentYearDuration',
             'ユニットID': 'JPY', '値': '1000'},
            # Per-filer custom namespace (Mizuho-shape)
            {'要素ID': 'jpcrp030000-asr_E03615-000:NetSales', 'コンテキストID': 'CurrentYearDuration',
             'ユニットID': 'JPY', '値': '2000'},
            # Insurance industry suffix
            {'要素ID': 'jpcrp_cor:NetSalesINS', 'コンテキストID': 'CurrentYearDuration',
             'ユニットID': 'JPY', '値': '3000'},
            # Unrelated element
            {'要素ID': 'jpcrp_cor:Assets', 'コンテキストID': 'CurrentYearInstant',
             'ユニットID': 'JPY', '値': '50000'},
        ],
    }]


def test_match_element_by_suffix_exact():
    """Exact suffix match: 'NetSales' matches 'jpcrp_cor:NetSales'."""
    matches = match_element_by_suffix(_csv_files_with_custom_namespaces(), 'NetSales')
    element_ids = sorted([m['要素ID'] for m in matches])
    # All three NetSales variants should match (canonical + custom-ns + INS)
    assert 'jpcrp_cor:NetSales' in element_ids
    assert 'jpcrp030000-asr_E03615-000:NetSales' in element_ids


def test_match_element_by_suffix_with_industry_suffixes():
    """When industry_suffixes=('INS', 'BNK'), also matches NetSalesINS / NetSalesBNK."""
    matches = match_element_by_suffix(
        _csv_files_with_custom_namespaces(), 'NetSales',
        industry_suffixes=('INS', 'BNK'),
    )
    element_ids = sorted([m['要素ID'] for m in matches])
    assert 'jpcrp_cor:NetSalesINS' in element_ids
    assert 'jpcrp_cor:NetSales' in element_ids


def test_match_element_by_suffix_excludes_unrelated():
    """Assets does not match NetSales suffix."""
    matches = match_element_by_suffix(_csv_files_with_custom_namespaces(), 'NetSales')
    element_ids = [m['要素ID'] for m in matches]
    assert 'jpcrp_cor:Assets' not in element_ids


def test_match_element_by_suffix_empty_when_no_match():
    matches = match_element_by_suffix(_csv_files_with_custom_namespaces(), 'NonExistentElement')
    assert matches == []


def test_match_element_by_suffix_returns_row_dicts():
    """Returns the raw CSV row dicts, not just element_ids."""
    matches = match_element_by_suffix(_csv_files_with_custom_namespaces(), 'NetSales')
    assert all(isinstance(m, dict) for m in matches)
    assert all('値' in m for m in matches)
