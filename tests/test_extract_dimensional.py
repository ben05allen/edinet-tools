"""Tests for extract_dimensional() — axis-context extraction primitive.

Per spec §4.2: returns DimensionalFact list with axis_members parsed
heuristically from context_id strings. Falls back gracefully (empty
axis_members) when context_id doesn't match expected patterns.
"""

from edinet_tools.parsers._dimensional import DimensionalFact, extract_dimensional


def _csv_files_with_segment_axis():
    """Synthetic CSV with axis-tagged segment values."""
    return [
        {
            "filename": "test.csv",
            "data": [
                {
                    "要素ID": "要素ID",
                    "項目名": "項目名",
                    "コンテキストID": "コンテキストID",
                    "相対年度": "",
                    "連結・個別": "",
                    "期間・時点": "",
                    "ユニットID": "",
                    "単位": "",
                    "値": "",
                },
                {
                    "要素ID": "jpcrp_cor:Sales",
                    "コンテキストID": "CurrentYearDuration_jpcrp_cor:ReportableSegment1Member",
                    "ユニットID": "JPY",
                    "値": "1000",
                },
                {
                    "要素ID": "jpcrp_cor:Sales",
                    "コンテキストID": "CurrentYearDuration_jpcrp_cor:ReportableSegment2Member",
                    "ユニットID": "JPY",
                    "値": "2000",
                },
                {
                    "要素ID": "jpcrp_cor:Sales",
                    "コンテキストID": "CurrentYearDuration_jpcrp_cor:ReportableSegmentsMember",
                    "ユニットID": "JPY",
                    "値": "3000",
                },
            ],
        }
    ]


def test_extract_dimensional_returns_DimensionalFact_list():
    facts = extract_dimensional(_csv_files_with_segment_axis(), "jpcrp_cor:Sales")
    assert all(isinstance(f, DimensionalFact) for f in facts)
    assert len(facts) == 3


def test_extract_dimensional_parses_axis_member():
    facts = extract_dimensional(_csv_files_with_segment_axis(), "jpcrp_cor:Sales")
    # axis_members is a list of (axis_name, member_name) tuples
    members = sorted(set(m[1] for f in facts for m in f.axis_members))
    assert "ReportableSegment1" in members
    assert "ReportableSegment2" in members
    assert "ReportableSegments" in members


def test_extract_dimensional_preserves_base_context():
    """base_context strips axis tokens; preserves the non-axis prefix."""
    facts = extract_dimensional(_csv_files_with_segment_axis(), "jpcrp_cor:Sales")
    for f in facts:
        assert f.base_context == "CurrentYearDuration"


def test_extract_dimensional_returns_empty_for_unknown_element():
    facts = extract_dimensional(_csv_files_with_segment_axis(), "jpcrp_cor:NonExistent")
    assert facts == []


def test_extract_dimensional_handles_no_axis_context():
    """Element without axis-tagged context_id returns DimensionalFact with empty axis_members."""
    csv_files = [
        {
            "filename": "test.csv",
            "data": [
                {
                    "要素ID": "要素ID",
                    "項目名": "項目名",
                    "コンテキストID": "コンテキストID",
                    "相対年度": "",
                    "連結・個別": "",
                    "期間・時点": "",
                    "ユニットID": "",
                    "単位": "",
                    "値": "",
                },
                {
                    "要素ID": "jpcrp_cor:NetSales",
                    "コンテキストID": "CurrentYearDuration",
                    "ユニットID": "JPY",
                    "値": "5000",
                },
            ],
        }
    ]
    facts = extract_dimensional(csv_files, "jpcrp_cor:NetSales")
    assert len(facts) == 1
    assert facts[0].axis_members == []
    assert facts[0].base_context == "CurrentYearDuration"
    assert facts[0].value == "5000"


def test_extract_dimensional_multiple_axes_in_one_context():
    """Context with two axis members (axis nesting) parses both."""
    csv_files = [
        {
            "filename": "test.csv",
            "data": [
                {
                    "要素ID": "要素ID",
                    "項目名": "項目名",
                    "コンテキストID": "コンテキストID",
                    "相対年度": "",
                    "連結・個別": "",
                    "期間・時点": "",
                    "ユニットID": "",
                    "単位": "",
                    "値": "",
                },
                {
                    "要素ID": "jpcrp_cor:Sales",
                    "コンテキストID": "CurrentYearDuration_jpcrp_cor:SegmentAMember_jpcrp_cor:NonConsolidatedMember",
                    "ユニットID": "JPY",
                    "値": "500",
                },
            ],
        }
    ]
    facts = extract_dimensional(csv_files, "jpcrp_cor:Sales")
    assert len(facts) == 1
    member_names = sorted([m[1] for m in facts[0].axis_members])
    assert "NonConsolidated" in member_names
    assert "SegmentA" in member_names


def test_extract_dimensional_value_preserved_as_string():
    """value field is the raw CSV string (no numeric coercion at primitive level)."""
    facts = extract_dimensional(_csv_files_with_segment_axis(), "jpcrp_cor:Sales")
    values = sorted([f.value for f in facts])
    assert values == ["1000", "2000", "3000"]


# ---------------------------------------------------------------------------
# Real-data + contract-pin hardening (per the 2026-05-22 false-confidence audit).
#
# `extract_dimensional` is a deliberate pass-through primitive: it returns one
# DimensionalFact per row matching element_id, parsing axis members from the
# context_id WITHOUT filtering. The caller resolves axes per spec §4.2. Two
# planned extractors (top-shareholders in 0.7.1, directors in 0.7.2) build on
# this; the segments class-of-bug — "no positive axis filter, caller relied on
# the primitive to discriminate" — would propagate if those extractors made
# the same assumption. These tests pin the contract and prove it works on
# real-filing CSV shapes the sanitized fixture above cannot reproduce.
# ---------------------------------------------------------------------------


def _load_segments_fixture(name: str):
    """Load tokio_marine_real_full.csv from the segments fixtures dir."""
    import csv as csv_module
    from pathlib import Path

    p = Path(__file__).parent / "fixtures" / "segments" / f"{name}.csv"
    with open(p, "r", encoding="utf-8") as f:
        rows = list(csv_module.reader(f, delimiter="\t"))
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
    return [{"filename": f"{name}.csv", "data": [dict(zip(columns, r)) for r in rows[1:]]}]


def test_extract_dimensional_is_axis_agnostic_contract():
    """Pin the no-filtering contract: the primitive must return facts for
    elements on ANY axis — operating segments, generic Row\\d enumeration,
    equity components — and let the caller resolve axes.

    Tested via two distinct elements that live on different axes in the
    Tokio Marine filing (no single element happens to span both)."""
    csv_files = _load_segments_fixture("tokio_marine_real_full")

    # (a) A segment-table element: NumberOfEmployees → operating-segment members.
    seg_facts = extract_dimensional(csv_files, "jpcrp_cor:NumberOfEmployees")
    seg_member_names = {m[1] for f in seg_facts for m in f.axis_members}
    assert any(n.endswith("ReportableSegments") for n in seg_member_names), (
        f"primitive dropped segment-axis members: {sorted(seg_member_names)[:8]}"
    )

    # (b) A wage-gap-table element: Row\\d members carry it. If the primitive
    # were quietly filtering to "real" axis members, these would be missing.
    row_facts = extract_dimensional(
        csv_files,
        "jpcrp_cor:RatioOfFemaleEmployeesInManagerialPositionsMetricsOfConsolidatedSubsidiaries",
    )
    row_member_names = {m[1] for f in row_facts for m in f.axis_members}
    assert any(n.startswith("Row") for n in row_member_names), (
        f"primitive dropped Row\\d enumeration members — it must be axis-agnostic, "
        f"not filter to 'real' members. got: {sorted(row_member_names)[:8]}"
    )


def test_extract_dimensional_handles_empty_inputs():
    """Defensive: None / empty / no-data fixtures return []."""
    assert extract_dimensional(None, "jpcrp_cor:Anything") == []
    assert extract_dimensional([], "jpcrp_cor:Anything") == []
    assert extract_dimensional([{"filename": "x.csv", "data": None}], "jpcrp_cor:Anything") == []
    assert extract_dimensional([{"filename": "x.csv", "data": []}], "jpcrp_cor:Anything") == []


def test_extract_dimensional_returns_exact_count_no_duplicates_or_drops():
    """The primitive must return EXACTLY one DimensionalFact per matching row —
    no de-duplication (different contexts are different facts), no silent drops."""
    csv_files = _load_segments_fixture("tokio_marine_real_full")
    # Count raw rows matching the element directly from the fixture.
    raw_match_count = sum(
        1
        for cf in csv_files
        for r in cf["data"]
        if r.get("要素ID") == "jpcrp_cor:NumberOfEmployees"
    )
    facts = extract_dimensional(csv_files, "jpcrp_cor:NumberOfEmployees")
    assert len(facts) == raw_match_count, (
        f"primitive returned {len(facts)} facts for {raw_match_count} raw rows — "
        "must be one-to-one, no dedup, no drops"
    )


def test_extract_dimensional_preserves_filer_extension_member_names():
    """Real EDINET context_ids carry per-filer extension namespace prefixes like
    `jpcrp030000-asr_E03847-000DomesticLifeInsuranceReportableSegmentsMember`.
    The primitive must extract the member name even when the prefix contains
    underscores (cannot naively split on '_')."""
    csv_files = _load_segments_fixture("tokio_marine_real_full")
    facts = extract_dimensional(csv_files, "jpcrp_cor:NumberOfEmployees")
    member_names = {m[1] for f in facts for m in f.axis_members}
    # The filer-extension-namespace members must survive the underscore-aware split.
    assert "DomesticLifeInsuranceReportableSegments" in member_names, (
        f"underscore-bearing namespace prefix broke member extraction. got: "
        f"{sorted(member_names)[:10]}"
    )
