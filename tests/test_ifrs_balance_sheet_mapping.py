"""IFRS balance-sheet fallbacks: element NAMES must exist in the real jpigp
taxonomy. The old map pointed current_liabilities at a non-existent
CurrentLiabilitiesIFRS (the real element is TotalCurrentLiabilitiesIFRS) and
had no DeferredTaxAssets / depreciation fallbacks at all.

Pinned values (from verified prod-fixture data, 2026-06-09):
  current_liabilities    = 3_146_299_000_000  (jpigp_cor:TotalCurrentLiabilitiesIFRS,
                                                CurrentYearInstant, MHI)
  deferred_tax_assets    =   259_942_000_000  (jpigp_cor:DeferredTaxAssetsIFRS,
                                                CurrentYearInstant, MHI)
  depreciation_amortization = 2_251_233_000_000 (jpigp_cor:DepreciationAndAmortizationOpeCFIFRS,
                                                  CurrentYearDuration, Toyota)
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


def test_ifrs_current_liabilities_recovered():
    # MHI (IFRS): current_liabilities must come from jpigp_cor:TotalCurrentLiabilitiesIFRS
    # (the previously-mapped CurrentLiabilitiesIFRS does not exist in the taxonomy).
    r = _parse('mhi_ifrs_blast_radius')
    assert r.accounting_standard == 'IFRS'
    assert r.current_liabilities == 3_146_299_000_000


def test_ifrs_deferred_tax_assets_recovered():
    # jpigp_cor:DeferredTaxAssetsIFRS, CurrentYearInstant, MHI
    r = _parse('mhi_ifrs_blast_radius')
    assert r.accounting_standard == 'IFRS'
    assert r.deferred_tax_assets == 259_942_000_000


def test_ifrs_depreciation_recovered():
    # jpigp_cor:DepreciationAndAmortizationOpeCFIFRS, CurrentYearDuration, Toyota
    r = _parse('toyota_fy25_revenue')
    assert r.accounting_standard == 'IFRS'
    assert r.depreciation_amortization == 2_251_233_000_000
