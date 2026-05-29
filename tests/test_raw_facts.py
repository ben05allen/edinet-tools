"""Tests for the new Fact dataclass + raw_facts field on ParsedReport.

Per spec §4.3: additive fact-bag preservation. Existing raw_fields
last-wins behavior unchanged; raw_facts preserves every
(element_id, context_id, value, unit_id) triple.
"""
from edinet_tools.parsers._facts import Fact
from edinet_tools.parsers.base import ParsedReport


def test_fact_dataclass_basic_construction():
    f = Fact(element_id='jpcrp_cor:NetSales', context_id='CurrentYearDuration',
             value='1000000000', unit_id='JPY')
    assert f.element_id == 'jpcrp_cor:NetSales'
    assert f.context_id == 'CurrentYearDuration'
    assert f.value == '1000000000'
    assert f.unit_id == 'JPY'


def test_fact_dataclass_unit_id_defaults_to_None():
    f = Fact(element_id='jpcrp_cor:DocumentTitle',
             context_id='FilingDateInstant', value='Report')
    assert f.unit_id is None


def test_parsed_report_has_raw_facts_field():
    report = ParsedReport(doc_id='S100TEST', doc_type_code='120')
    assert hasattr(report, 'raw_facts')
    assert report.raw_facts == []


def test_parsed_report_raw_facts_accepts_facts():
    facts = [
        Fact('jpcrp_cor:NetSales', 'CurrentYearDuration', '1000', 'JPY'),
        Fact('jpcrp_cor:NetSales', 'PriorYearDuration', '900', 'JPY'),
    ]
    report = ParsedReport(doc_id='S100TEST', doc_type_code='120', raw_facts=facts)
    assert len(report.raw_facts) == 2
    assert report.raw_facts[0].context_id == 'CurrentYearDuration'
    assert report.raw_facts[1].value == '900'


def test_parsed_report_existing_fields_unchanged():
    report = ParsedReport(
        doc_id='S100TEST', doc_type_code='120',
        raw_fields={'jpcrp_cor:NetSales': '1000'},
        text_blocks={'BusinessOverviewTextBlock': '...'},
        unmapped_fields={'jpdei_cor:Unknown': 'value'},
    )
    assert report.raw_fields == {'jpcrp_cor:NetSales': '1000'}
    assert report.text_blocks == {'BusinessOverviewTextBlock': '...'}
    assert report.unmapped_fields == {'jpdei_cor:Unknown': 'value'}
    assert report.raw_facts == []


def test_categorize_elements_populates_raw_facts():
    """categorize_elements now returns raw_facts as a fourth value."""
    from edinet_tools.parsers.extraction import categorize_elements

    csv_files = [{
        'filename': 'test.csv',
        'data': [
            {'要素ID': '要素ID', '項目名': '項目名', 'コンテキストID': 'コンテキストID',
             '相対年度': '', '連結・個別': '', '期間・時点': '', 'ユニットID': '', '単位': '', '値': ''},
            {'要素ID': 'jpcrp_cor:NetSales', 'コンテキストID': 'CurrentYearDuration',
             'ユニットID': 'JPY', '値': '1000'},
            {'要素ID': 'jpcrp_cor:NetSales', 'コンテキストID': 'PriorYearDuration',
             'ユニットID': 'JPY', '値': '900'},
            {'要素ID': 'jpcrp_cor:BusinessOverviewTextBlock', 'コンテキストID': 'CurrentYearDuration',
             'ユニットID': '', '値': 'overview text'},
        ],
    }]
    result = categorize_elements(csv_files)
    raw_fields, text_blocks, unmapped_fields, raw_facts = result

    assert 'jpcrp_cor:NetSales' in raw_fields
    netsales_facts = [f for f in raw_facts if f.element_id == 'jpcrp_cor:NetSales']
    assert len(netsales_facts) == 2
    contexts = {f.context_id for f in netsales_facts}
    assert contexts == {'CurrentYearDuration', 'PriorYearDuration'}


def test_categorize_elements_raw_facts_includes_unit_id():
    from edinet_tools.parsers.extraction import categorize_elements
    csv_files = [{
        'filename': 'test.csv',
        'data': [
            {'要素ID': '要素ID', '項目名': '項目名', 'コンテキストID': 'コンテキストID',
             '相対年度': '', '連結・個別': '', '期間・時点': '', 'ユニットID': '', '単位': '', '値': ''},
            {'要素ID': 'jpcrp_cor:NetSales', 'コンテキストID': 'CurrentYearDuration',
             'ユニットID': 'JPY', '値': '1000'},
        ],
    }]
    _, _, _, raw_facts = categorize_elements(csv_files)
    assert raw_facts[0].unit_id == 'JPY'


def test_categorize_elements_returns_4_tuple_of_correct_types():
    from edinet_tools.parsers.extraction import categorize_elements
    csv_files = [{
        'filename': 'test.csv',
        'data': [
            {'要素ID': '要素ID', '項目名': '項目名', 'コンテキストID': 'コンテキストID',
             '相対年度': '', '連結・個別': '', '期間・時点': '', 'ユニットID': '', '単位': '', '値': ''},
            {'要素ID': 'jpcrp_cor:NetSales', 'コンテキストID': 'CurrentYearDuration', '値': '1000'},
        ],
    }]
    result = categorize_elements(csv_files)
    assert len(result) == 4
    raw_fields, text_blocks, unmapped_fields, raw_facts = result
    assert isinstance(raw_fields, dict)
    assert isinstance(text_blocks, dict)
    assert isinstance(unmapped_fields, dict)
    assert isinstance(raw_facts, list)
