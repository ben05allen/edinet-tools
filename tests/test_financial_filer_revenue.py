"""Financial-sector filers (8699 HS Holdings: securities) report revenue as
OperatingRevenue (営業収益), not NetSales. Without the mapping, net_sales is
NULL or a tiny sub-line and operating_income > net_sales (impossible margin).
"""
import csv as _csv
from pathlib import Path
from edinet_tools.parsers.securities import parse_securities_report

_COLS = ['要素ID', '項目名', 'コンテキストID', '相対年度',
         '連結・個別', '期間・時点', 'ユニットID', '単位', '値']


def _parse(name):
    p = Path(__file__).parent / 'fixtures' / 'securities' / f'{name}.csv'
    with open(p, encoding='utf-8') as fh:
        rows = list(_csv.reader(fh, delimiter='\t'))
    cf = [{'filename': f'{name}.csv', 'data': [dict(zip(_COLS, r)) for r in rows[1:]]}]
    return parse_securities_report(csv_files=cf, doc_id='TEST', doc_type_code='120')


def test_financial_filer_net_sales_from_operating_revenue():
    r = _parse('hsholdings_fy_revenue')
    assert r.net_sales == 37766000000
    assert r.prior_net_sales == 49597000000
    # impossible-margin gone
    assert r.operating_income is None or r.operating_income <= r.net_sales
