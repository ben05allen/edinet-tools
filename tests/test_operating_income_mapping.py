"""Golden tests: operating_income must never be the parent J-GAAP line for
IFRS/US-GAAP consolidated filers. Trading houses (no IFRS operating subtotal)
get honest None; filers that DO report an IFRS/US-GAAP operating line keep it.
"""
import csv as _csv
from pathlib import Path
import pytest
from edinet_tools.parsers.securities import parse_securities_report

_COLS = ['要素ID', '項目名', 'コンテキストID', '相対年度',
         '連結・個別', '期間・時点', 'ユニットID', '単位', '値']

def _load(name):
    p = Path(__file__).parent / 'fixtures' / 'securities' / f'{name}.csv'
    rows = list(_csv.reader(open(p, encoding='utf-8'), delimiter='\t'))
    return [{'filename': f'{name}.csv', 'data': [dict(zip(_COLS, r)) for r in rows[1:]]}]

def _parse(name):
    return parse_securities_report(csv_files=_load(name), doc_id='TEST', doc_type_code='120')

def test_ifrs_trading_house_operating_income_is_none():
    # 8001 Itochu: IFRS P&L has no operating-profit subtotal -> honest None,
    # NOT the parent J-GAAP jppfs_cor:OperatingIncome leak.
    r = _parse('itochu_fy25_op_income')
    assert r.accounting_standard == 'IFRS'
    assert r.operating_income is None, f'expected None, got {r.operating_income}'
    # regression guard: revenue still correct
    assert r.net_sales and r.net_sales > 10_000_000_000_000

def test_ifrs_filer_with_real_operating_line_preserved():
    # 8015 Toyota Tsusho: reports jpigp_cor:OperatingProfitLossIFRS (consolidated) -> keep it.
    # EXACT pin: a magnitude check alone would also pass on a leaked parent value.
    r = _parse('toyotatsusho_fy25_op_income')
    assert r.accounting_standard == 'IFRS'
    assert r.operating_income == 497_174_000_000
    assert r.prior_operating_income == 441_589_000_000

def test_usgaap_operating_income_from_summary_element():
    # Sony US-GAAP: has jpcrp_cor:OperatingIncomeLossUSGAAPSummaryOfBusinessResults.
    # EXACT pin: only the exact value proves the right element won.
    r = _parse('sony_fy20_usgaap_revenue')
    assert r.accounting_standard == 'US GAAP'
    assert r.operating_income == 845_459_000_000
    assert r.prior_operating_income == 894_235_000_000

def test_jgaap_operating_income_unchanged():
    # Control: J-GAAP path must keep working (jppfs_cor:OperatingIncome).
    r = _parse('jgaap_control_revenue')
    assert r.accounting_standard == 'Japan GAAP'
    assert r.operating_income is not None
