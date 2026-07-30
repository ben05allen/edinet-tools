"""Tests for the segments parser layer.

Two layers tested separately:
1. SegmentRow dataclass + parse_segments_from_csv() (this task + Task 8)
2. parse_securities_report() integration (Task 9)

Real-EDINET fixture-driven regression tests (Task 10).
"""

import pytest

from edinet_tools.parsers.segments import SegmentRow


def test_segment_row_dataclass_basic():
    row = SegmentRow(
        segment_name="Asia-Pacific",
        axis_family="OperatingSegments",
        metrics={"Sales": "100000000", "OperatingProfit": "5000000"},
        period="CurrentYear",
        consolidation_axis="Consolidated",
    )
    assert row.segment_name == "Asia-Pacific"
    assert row.axis_family == "OperatingSegments"
    assert row.metrics["Sales"] == "100000000"
    assert row.period == "CurrentYear"
    assert row.consolidation_axis == "Consolidated"


def test_segment_row_consolidation_axis_optional():
    """consolidation_axis defaults to None (most filings are consolidated)."""
    row = SegmentRow(
        segment_name="Materials",
        axis_family="OperatingSegments",
        metrics={"Sales": "500"},
        period="CurrentYear",
    )
    assert row.consolidation_axis is None


def test_securities_report_has_segments_field():
    """SecuritiesReport gains segments + segments_text_only fields."""
    from edinet_tools.parsers.securities import SecuritiesReport

    report = SecuritiesReport(doc_id="S100TEST", doc_type_code="120")
    assert hasattr(report, "segments")
    assert hasattr(report, "segments_text_only")
    assert report.segments == []
    assert report.segments_text_only is False


def _load_fixture(name: str):
    """Load a test fixture CSV into the csv_files structure."""
    import csv as csv_module
    from pathlib import Path

    fixture_path = Path(__file__).parent / "fixtures" / "segments" / f"{name}.csv"
    with open(fixture_path, "r", encoding="utf-8") as f:
        reader = csv_module.reader(f, delimiter="\t")
        rows = list(reader)
    if not rows:
        return []
    columns = [
        "要素ID",
        "項目名",
        "コンテキストID",
        "相対年度",
        "連結・個別",
        "期間・時点",
        "ユニットID",
        "単位",
        "値",
    ]
    # First row is the column-name header; rest are data
    data = [dict(zip(columns, row)) for row in rows[1:]]
    return [{"filename": f"{name}.csv", "data": data}]


def test_parse_segments_from_csv_recruit_ifrs():
    """Recruit IFRS filer: axis-discrete segments parse to multiple SegmentRow.

    Fixture shape: jpigp_cor:SegmentProfitLossIFRS + jpigp_cor:IntersegmentRevenueIFRS
    with per-filer custom namespace context IDs like:
    CurrentYearDuration_jpcrp030000-asr_E07801-000HRTechnologyReportableSegmentMember
    Member name extracted: 'HRTechnologyReportableSegment' (filer prefix stripped).
    """
    from edinet_tools.parsers.segments import parse_segments_from_csv

    csv_files = _load_fixture("recruit_ifrs")
    segments, segments_text_only, _ = parse_segments_from_csv(csv_files)

    assert segments_text_only is False
    segment_names = {s.segment_name for s in segments}
    # EXACT set — the 3 reportable segments + 2 aggregation rows.
    assert segment_names == {
        "HRTechnologyReportableSegment",
        "MatchingAndSolutionsReportableSegment",
        "StaffingReportableSegments",
        "ReconcilingItems",
        "TotalOfReportableSegmentsAndOthers",
    }, f"unexpected segment set: {segment_names}"
    # axis_family classification: operating segments vs aggregation.
    by_family = {s.segment_name: s.axis_family for s in segments}
    assert by_family["HRTechnologyReportableSegment"] == "OperatingSegments"
    assert by_family["ReconcilingItems"] == "TotalReconciling"


def test_parse_segments_from_csv_daikin_jgaap_has_reconciling():
    """Daikin J-GAAP: includes Total/Reconciling row separately from individual segments.

    Fixture shape: jppfs_cor:NetSales + jppfs_cor:OperatingIncome with per-filer
    custom namespace members like:
    AirConditioningAndRefrigerationEquipmentReportableSegments,
    plus ReconcilingItemsMember and TotalOfReportableSegmentsAndOthersMember.
    """
    from edinet_tools.parsers.segments import parse_segments_from_csv

    csv_files = _load_fixture("daikin_jgaap")
    segments, segments_text_only, _ = parse_segments_from_csv(csv_files)

    assert segments_text_only is False
    segment_names = {s.segment_name for s in segments}
    # EXACT set: 2 reportable segments + 4 aggregation/other rows.
    assert segment_names == {
        "AirConditioningAndRefrigerationEquipmentReportableSegments",
        "ChemicalsReportableSegments",
        "OperatingSegmentsNotIncludedInReportableSegmentsAndOtherRevenueGeneratingBusinessActivities",
        "ReconcilingItems",
        "ReportableSegments",
        "TotalOfReportableSegmentsAndOthers",
    }, f"unexpected segment set: {segment_names}"
    # The two operating segments carry segment financials (NetSales/OperatingIncome).
    op_segs = [s for s in segments if s.axis_family == "OperatingSegments"]
    assert any("NetSales" in s.metrics for s in op_segs), (
        "expected NetSales in operating segment metrics"
    )


def test_parse_segments_from_csv_mufg_bank_custom_namespace():
    """MUFG bank: per-filer custom-namespace member names without standard 'Segment' token.

    Fixture shape: jpcrp_cor:DepreciationSegmentInformation with context IDs like:
    CurrentYearDuration_jpcrp030000-asr_E03606-000RetailAndDigitalBusinessGroupMember
    Member names use E03606-000 prefix (NOT E03615 as plan guessed — suffix matcher
    is namespace-agnostic so this works regardless).
    Members: RetailAndDigitalBusinessGroup, CommercialBankingAndWealthManagementBusinessGroup, etc.
    """
    from edinet_tools.parsers.segments import parse_segments_from_csv

    csv_files = _load_fixture("mufg_bank")
    segments, segments_text_only, _ = parse_segments_from_csv(csv_files)

    assert segments_text_only is False
    segment_names = {s.segment_name for s in segments}
    # EXACT set: 7 BusinessGroup segments + 3 aggregation (Other/Total/TotalOfCustomerBusinessUnit).
    # Validates the BusinessGroup suffix is recognized as a segment-axis convention
    # (not just ReportableSegment), which is the key MUFG-specific shape.
    assert segment_names == {
        "AssetManagementAndInvestorServicesBusinessGroup",
        "CommercialBankingAndWealthManagementBusinessGroup",
        "GlobalCommercialBankingBusinessGroup",
        "GlobalCorporateAndInvestmentBankingBusinessGroup",
        "GlobalMarketsBusinessGroup",
        "JapaneseCorporateAndInvestmentBankingBusinessGroup",
        "RetailAndDigitalBusinessGroup",
        "Other",
        "Total",
        "TotalOfCustomerBusinessUnit",
    }, f"unexpected segment set: {segment_names}"
    # The 7 BusinessGroup members are operating segments, not aggregation.
    op_segs = {s.segment_name for s in segments if s.axis_family == "OperatingSegments"}
    assert len(op_segs) == 7 and all(n.endswith("BusinessGroup") for n in op_segs)


def test_parse_segments_from_csv_temairazu_nonconsolidated_nesting():
    """Temairazu parent-only filer: NonConsolidatedMember nests BEFORE SegmentMember.

    Fixture shape: jppfs_cor:NetSales + jppfs_cor:OperatingIncome with context IDs like:
    Prior1YearDuration_NonConsolidatedMember_jpcrp030000-asr_E05564-000ApplicationServiceReportableSegmentMember
    The NonConsolidatedMember is the FIRST axis member; segment name is SECOND.
    Parser must order-preservingly classify the first as consolidation_axis, second as segment_name.
    """
    from edinet_tools.parsers.segments import parse_segments_from_csv

    csv_files = _load_fixture("temairazu_nonconsolidated")
    segments, segments_text_only, _ = parse_segments_from_csv(csv_files)

    # Temairazu IS axis-discrete (parent-only filer with NonConsolidatedMember-nested segments).
    # Drop the vacuous `if segments:` gate — require non-empty AND correct axis capture.
    assert segments_text_only is False
    assert len(segments) > 0, "Temairazu has axis-discrete segments; parser must extract them"
    segment_names = {s.segment_name for s in segments}
    # EXACT set: 2 reportable segments + 2 aggregation rows.
    assert segment_names == {
        "ApplicationServiceReportableSegment",
        "InternetMediaReportableSegment",
        "ReconcilingItems",
        "TotalOfReportableSegmentsAndOthers",
    }, f"unexpected segment set: {segment_names}"
    # The NonConsolidatedMember axis nesting must be captured as consolidation_axis.
    consolidation_values = {s.consolidation_axis for s in segments}
    assert "NonConsolidated" in consolidation_values, (
        f"NonConsolidated axis nesting lost; consolidation_values={consolidation_values}"
    )


def test_parse_segments_from_csv_komatsu_usgaap_textblock_fallback():
    """Komatsu US-GAAP filer: segment data buried in TextBlock; parser must signal
    segments_text_only=True and return empty list of segments.

    Fixture shape: no axis-discrete segment rows; has BusinessResultsOfGroupTextBlock
    containing '米国会計基準' (US accounting standards). Parser detects this and sets
    the fallback flag.
    """
    from edinet_tools.parsers.segments import parse_segments_from_csv

    csv_files = _load_fixture("komatsu_usgaap")
    segments, segments_text_only, _ = parse_segments_from_csv(csv_files)

    # US-GAAP filer with no axis-discrete segments: BOTH must hold — the fallback
    # flag is set AND the segments list is empty. The previous `or` formulation
    # passed vacuously when zero segments were extracted for the wrong reason.
    assert segments_text_only is True, "US-GAAP fallback flag must be set for Komatsu"
    assert segments == [], f"expected empty segments for text-only filer, got {len(segments)}"


def test_parse_segments_from_csv_dash_null_coercion():
    """'－' placeholder in metric value coerces to absent / None in metrics dict."""
    from edinet_tools.parsers.segments import parse_segments_from_csv

    # Use realistic ReportableSegment-suffix member names so the anchored-union
    # discriminator recognizes them (bare 'SegmentAMember' would not match the
    # segment-axis naming convention — that's by design, not a coercion bug).
    csv_files = [
        {
            "filename": "dash_test.csv",
            "data": [
                {
                    "要素ID": "jpcrp_cor:Sales",
                    "コンテキストID": "CurrentYearDuration_jpcrp_cor:SegmentAReportableSegmentMember",
                    "ユニットID": "JPY",
                    "値": "1000",
                },
                {
                    "要素ID": "jpcrp_cor:Sales",
                    "コンテキストID": "CurrentYearDuration_jpcrp_cor:SegmentBReportableSegmentMember",
                    "ユニットID": "JPY",
                    "値": "－",
                },  # dash null
            ],
        }
    ]
    segments, _segments_text_only, _ = parse_segments_from_csv(csv_files)

    # Both must be present (no vacuous-pass via missing member).
    by_name = {s.segment_name: s for s in segments}
    assert "SegmentAReportableSegment" in by_name, f"SegmentA missing: {list(by_name)}"
    assert "SegmentBReportableSegment" in by_name, f"SegmentB missing: {list(by_name)}"
    # A has the numeric value; B's '－' must coerce to absent (not stored).
    assert by_name["SegmentAReportableSegment"].metrics.get("Sales") == "1000"
    assert "Sales" not in by_name["SegmentBReportableSegment"].metrics, (
        "dash placeholder must coerce to None and be omitted from metrics"
    )


def test_parse_securities_report_populates_segments():
    """parse_securities_report() now populates the segments field."""
    from edinet_tools.parsers.securities import parse_securities_report

    csv_files = _load_fixture("recruit_ifrs")
    report = parse_securities_report(csv_files=csv_files, doc_id="S100TEST", doc_type_code="120")

    # segments field is populated with the exact recruit_ifrs segment set
    # (3 reportable segments + 2 aggregation rows; rows = names × periods/axes).
    assert hasattr(report, "segments")
    assert isinstance(report.segments, list)
    names = {s.segment_name for s in report.segments}
    assert names == {
        "HRTechnologyReportableSegment",
        "MatchingAndSolutionsReportableSegment",
        "StaffingReportableSegments",
        "ReconcilingItems",
        "TotalOfReportableSegmentsAndOthers",
    }, f"unexpected segment set on parsed report: {names}"


def test_parse_securities_report_segments_text_only_flag_on_komatsu():
    """parse_securities_report() sets segments_text_only=True on US-GAAP filer."""
    from edinet_tools.parsers.securities import parse_securities_report

    csv_files = _load_fixture("komatsu_usgaap")
    report = parse_securities_report(csv_files=csv_files, doc_id="S100TEST", doc_type_code="120")

    assert report.segments_text_only is True
    assert report.segments == []


def test_parse_securities_report_preserves_existing_fields():
    """Adding segments to parser must not affect raw_fields / text_blocks / unmapped_fields
    or any other existing extraction behavior. Per fact-bag-preservation principle."""
    from edinet_tools.parsers.securities import parse_securities_report

    csv_files = _load_fixture("recruit_ifrs")
    report = parse_securities_report(csv_files=csv_files, doc_id="S100TEST", doc_type_code="120")

    # All other fact-bag fields populate
    assert hasattr(report, "raw_fields")
    assert isinstance(report.raw_fields, dict)
    assert hasattr(report, "text_blocks")
    assert isinstance(report.text_blocks, dict)
    assert hasattr(report, "unmapped_fields")
    assert isinstance(report.unmapped_fields, dict)
    assert hasattr(report, "raw_facts")
    assert isinstance(report.raw_facts, list)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "recruit_ifrs",
        "daikin_jgaap",
        "mufg_bank",
        "temairazu_nonconsolidated",
        "komatsu_usgaap",
    ],
)
def test_fact_bag_preserved_alongside_segments(fixture_name):
    """For every fixture, raw_fields / text_blocks / unmapped_fields populate
    alongside segments. Per spec §3.1 fact-bag preservation principle."""
    from edinet_tools.parsers.securities import parse_securities_report

    csv_files = _load_fixture(fixture_name)
    report = parse_securities_report(csv_files=csv_files, doc_id="S100TEST", doc_type_code="120")

    # Some bucket should populate from the fixture's elements
    total_populated = (
        len(report.raw_fields)
        + len(report.text_blocks)
        + len(report.unmapped_fields)
        + len(report.raw_facts)
    )
    assert total_populated > 0, f"all fact-bag buckets empty for {fixture_name} — extraction broke"

    # raw_facts should be non-empty for any fixture with rows
    assert len(report.raw_facts) > 0, f"raw_facts empty for {fixture_name}"


def test_segments_parsing_does_not_pollute_raw_fields():
    """raw_fields[elem_id] last-wins behavior unchanged after segments parsing."""
    from edinet_tools.parsers.securities import parse_securities_report

    csv_files = _load_fixture("recruit_ifrs")
    report = parse_securities_report(csv_files=csv_files, doc_id="S100TEST", doc_type_code="120")

    # raw_fields is dict — no duplicates per key
    assert isinstance(report.raw_fields, dict)
    for elem_id, value in report.raw_fields.items():
        assert isinstance(elem_id, str)
        assert isinstance(value, str)


# ---------------------------------------------------------------------------
# Real full-filing regression: the sanitized fixtures above contain ONLY
# segment rows, so they cannot prove non-segment members are EXCLUDED. This
# fixture is a real Tokio Marine (8766) Doc 120 subset that ALSO contains
# director-name, equity-component, share-class, and generic Row\d members.
# Pre-fix, parse_segments_from_csv swept all of these in (628 garbage rows).
# ---------------------------------------------------------------------------

_TOKIO_MARINE_EXPECTED_SEGMENTS = {
    "DomesticPropertyAndCasualtyInsuranceReportableSegments",
    "DomesticLifeInsuranceReportableSegments",
    "OverseasInsuranceReportableSegments",
    "FinancialAndOtherReportableSegments",
    "ReportableSegments",  # aggregation (total of reportable segments)
    "ReconcilingItems",  # aggregation
}

# Non-segment members present in the fixture that MUST be excluded.
_TOKIO_MARINE_NOISE_MEMBERS = {
    "Row1",
    "Row2",
    "Row3",  # generic enumeration (wage-gap table)
    "ShareholdersEquity",
    "RetainedEarnings",
    "CapitalStock",
    "TreasuryStock",
    "DeferredGainsOrLossesOnHedges",
    "ForeignCurrencyTranslationAdjustment",  # equity components
    "OrdinaryShare",  # share class
    "SatoruKomiya",
    "RobertFeldman",  # director names
}


def test_real_full_filing_excludes_noise_members():
    """Exact segment set + zero noise from a real filing containing noise rows."""
    import re

    from edinet_tools.parsers.segments import parse_segments_from_csv

    csv_files = _load_fixture("tokio_marine_real_full")
    segments, segments_text_only, _ = parse_segments_from_csv(csv_files)

    assert segments_text_only is False
    names = {s.segment_name for s in segments}

    # EXACT set — no over-extraction, no missing segments.
    assert names == _TOKIO_MARINE_EXPECTED_SEGMENTS, (
        f"unexpected segment set.\n  extra:   {names - _TOKIO_MARINE_EXPECTED_SEGMENTS}\n"
        f"  missing: {_TOKIO_MARINE_EXPECTED_SEGMENTS - names}"
    )
    # Explicit absence assertions (the regression the sanitized fixtures lacked).
    assert not (names & _TOKIO_MARINE_NOISE_MEMBERS), (
        f"noise leaked: {names & _TOKIO_MARINE_NOISE_MEMBERS}"
    )
    assert not any(re.match(r"^(Row|Item|No)\d", n) for n in names), (
        f"generic member leaked: {names}"
    )
    # The 4 real operating segments carry segment financials.
    op = {s.segment_name for s in segments if s.axis_family == "OperatingSegments"}
    assert op == {
        "DomesticPropertyAndCasualtyInsuranceReportableSegments",
        "DomesticLifeInsuranceReportableSegments",
        "OverseasInsuranceReportableSegments",
        "FinancialAndOtherReportableSegments",
    }, f"operating-segment classification wrong: {op}"


def test_kurita_no_anchor_segments_extracted():
    """Industry/sector-named segments (no suffix anchor) must still extract.

    Kurita FY25 names its operating segments ElectronicsIndustry / GeneralIndustry —
    neither ends in a segment-axis suffix, so the anchored-union discriminator finds
    no anchors and (pre-fix) returns a silent []. The seed-from-aggregation path
    recovers them from the segment-specific aggregation rows while keeping
    equity / director / shareholder noise out (real noise present in the fixture).
    """
    from edinet_tools.parsers.segments import parse_segments_from_csv

    segments, segments_text_only, extraction_incomplete = parse_segments_from_csv(
        _load_fixture("kurita_no_anchor")
    )

    assert segments_text_only is False
    assert extraction_incomplete is False  # segments were successfully extracted
    op = {s.segment_name for s in segments if s.axis_family == "OperatingSegments"}
    assert op == {"ElectronicsIndustry", "GeneralIndustry"}, f"got {op}"
    names = {s.segment_name for s in segments}
    for noise in (
        "RetainedEarnings",
        "CapitalStock",
        "TreasuryStock",
        "ShareholdersEquity",
        "No1MajorShareholders",
        "AmanoKatsuya",
        "Row1",
    ):
        assert noise not in names, f"noise member leaked as segment: {noise}"


def test_jal_no_anchor_excludes_reconciliation_artifact():
    """A reconciliation artifact sharing the segment element profile is NOT a segment.

    JAL FY24 carries a `DividendsReceived` member with the same IFRS segment element
    profile (RevenueIFRS / IntersegmentRevenueIFRS / ProfitLossBeforeTaxIFRS …) as the
    reconciliation rows. It is the ONLY such non-aggregation member (< 2 real
    segments), so the segment table is not reconstructable — the parser must NOT
    hallucinate it as a segment. Guards the seed path against re-introducing noise.
    """
    from edinet_tools.parsers.segments import parse_segments_from_csv

    segments, _segments_text_only, extraction_incomplete = parse_segments_from_csv(
        _load_fixture("jal_no_anchor")
    )
    names = {s.segment_name for s in segments}
    assert "DividendsReceived" not in names, "reconciliation artifact leaked as a segment"
    # Segment-specific aggregation rows are present but no segments were extractable
    # → honest incomplete flag rather than a silent empty list.
    assert not segments and extraction_incomplete is True
    for noise in ("RetainedEarnings", "CapitalStock", "ShareholdersEquity"):
        assert noise not in names, f"noise member leaked as segment: {noise}"
