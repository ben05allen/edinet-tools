# Changelog

## v0.7.1 — 2026-06-10

Correctness release for the securities report parser: per-standard income-statement selection for IFRS and US-GAAP filers, several element mappings that pointed at XBRL ids that do not exist in real filings, and revenue coverage for financial-sector filers (banks, insurers, securities firms).

### Fixed

- **`operating_income` is now selected per accounting standard.** The coalesce tried the J-GAAP `jppfs_cor:OperatingIncome` first for every filer, which for IFRS/US-GAAP companies could only ever match a parent-company figure. IFRS filers now read their own operating-profit elements (`OperatingProfitLossIFRSSummaryOfBusinessResults`, then `jpigp_cor:OperatingProfitLossIFRS`); US-GAAP filers read `OperatingIncomeLossUSGAAPSummaryOfBusinessResults` — correcting v0.7.0's claim that no such element exists (Sony and others tag it). Filers whose statements have no operating-profit subtotal (IFRS trading houses, TextBlock-only US-GAAP filers) return honest `None` instead of a wrong number. Current and prior year.
- **IFRS `equity_ratio` stored equity-per-share in yen.** `jpcrp_cor:EquityToAssetRatioIFRSSummaryOfBusinessResults` is a taxonomy misnomer — its label is 1株当たり親会社所有者帰属持分 (equity attributable to owners of parent, per share). `equity_ratio` now reads the real ratio element `RatioOfOwnersEquityToGrossAssetsIFRSSummaryOfBusinessResults`; the per-share element continues to feed `ifrs_summary_bps`, which was already correct.
- **IFRS balance-sheet fallbacks pointed at a non-existent element.** `current_liabilities` mapped to `jpigp_cor:CurrentLiabilitiesIFRS`, which does not exist in real filings (the real element is `TotalCurrentLiabilitiesIFRS`), so the field was always `None` for IFRS filers. Also added the missing `DeferredTaxAssetsIFRS` and `DepreciationAndAmortizationOpeCFIFRS` fallbacks.
- **The J-GAAP cash-flow statement fallback tier was dead.** All three ids (`jpcrp_cor:CashFlowsFrom{Operating,Investment,Financing}Activities`) do not exist in real filings; replaced with the real `jppfs_cor:NetCashProvidedByUsedIn{Operating,Investment,Financing}Activities`.

### Added

- **Financial-sector revenue.** `net_sales` now reads `jppfs_cor:OperatingRevenue1` (営業収益 — securities firms and similar) and `jpcrp_cor:OrdinaryIncomeSummaryOfBusinessResults` (経常収益 — banks and insurers) when the standard revenue elements are absent. Previously these filers had `net_sales = None` or picked up a small sub-business line, producing impossible margins. Known gap: securities firms that tag only `OperatingRevenueSEC`-variant elements instead of `OperatingRevenue1` still return `None` — mapping planned for a future release.
- **US-GAAP summary balance sheet and cash flows.** `total_assets`, `net_assets`, `equity_ratio`, `net_assets_per_share`, and the operating/investing/financing cash flows now map the corresponding `...USGAAPSummaryOfBusinessResults` elements. These were all `None` for US-GAAP filers despite being present in their filings.

### Tests

- Five new real-filing golden fixtures (Itochu, Toyota Tsusho, HS Holdings, MUFG, Canon) with exact-value pins; the per-standard gate is mutation-tested. Test count: 798 → 832.
- Parsed output cross-checked against the issuers' own earnings releases for 20 filings across J-GAAP, IFRS, and US GAAP (banks, insurers, securities firms, trading companies, US-GAAP industrials): every populated figure matched to the yen.

### Note for existing databases

Parser fixes apply on (re-)parse. Data extracted with earlier versions keeps its old values — re-extract IFRS/US-GAAP and financial-sector filings to replace stale figures (including values that should now be honest `None`; make sure your update path writes `None` over previous values rather than skipping it).

## v0.7.0 — 2026-05-29

Segment-information parsing, a consolidated-revenue data-quality fix for IFRS/US-GAAP filers, registry-based filer classification, and the fact-shaped API transition (`Entity.entity_type`).

### Added

- **`SegmentRow` + `parse_segments_from_csv()`** — per-segment metrics from annual securities reports. Anchored-union discriminator (anchor on segment-name suffixes; admit aggregation rows only when they carry a segment-exclusive element), plus a no-anchor path that recovers industry/sector-named segments by seeding from segment-specific aggregation rows. Zero over-extraction across the broad-sample harness.
- **`SecuritiesReport` fields**: `segments`, `segments_text_only` (segment data in HTML text-blocks, not CSV), `segments_extraction_incomplete` (aggregation rows present but no segments extracted — honest miss flag).
- **US-GAAP summary income-statement elements** mapped (revenue, profit-before-tax, net income, EPS, ROE) — US-GAAP filers previously extracted as `None`. No operating-income line in the US-GAAP summary, so `operating_income` is honestly `None`.
- **`LargeHoldingReport.is_joint_filing`** — derived from `FilerLargeVolumeHolder<N>Member` axis presence (N ≥ 2), not hardcoded `False`.
- **`Fact` + `ParsedReport.raw_facts`** — typed access to the full XBRL fact set, alongside `raw_fields` / `text_blocks` / `unmapped_fields`.
- **`extract_dimensional()`** — axis-context primitive with member-name cleaning; substrate for segments and future schedule-table parsers.
- **`Entity.entity_type`** (`EntityType` enum) — fact-shaped FSA-registry classification; replaces the deprecated `is_listed` / `is_fund_issuer` booleans.
- **`extract_csv_to_disk()` + `Document.save_extracted_csvs()`** — disk-output helpers complementing in-memory `extract_csv_from_zip()`.

### Fixed

- **Consolidated revenue for IFRS / US-GAAP filers** — `net_sales` (and other income-statement metrics) returned the non-consolidated **parent** figure (e.g. ¥18T parent vs ¥48T consolidated). Now a consolidated filer never substitutes the parent value: a missing consolidated value falls through to the next element/tier or to honest `None` (parent stays in the fact-bag). With IFRS/US-GAAP/custom-namespace revenue elements mapped, the full cohort reads consolidated. Pinned by real-filing golden fixtures.
- **Holder names HTML-unescaped** — `_normalize_holder_value` applies `html.unescape`, so Doc 350 filer names with `&amp;` etc. are clean text.
- **`ExtraordinaryReport` / `SemiAnnualReport` filer classification** — `is_fund` returned `True` for ~all recent corporate filings (EDINET `'－'` placeholders broke the DEI heuristic). Now classified via the FSA registry (`report.filer.entity_type`); parsers expose `filer_edinet_code` as a fact.
- **`TreasuryStockReport` authorization flags** — `has_board_authorization` / `has_shareholder_authorization` no longer return `True` for empty/whitespace text blocks.
- **`QuarterlyReport.is_consolidated` and `SecuritiesReport.is_consolidated`** now return `None` when the `WhetherConsolidatedFinancialStatementsArePreparedDEI` element is missing, rather than silently defaulting to `True`. Honest unknowns over silent-failure-as-default.
- **`extract_dimensional()` member names** are stripped of per-filer extension namespace prefixes (e.g., `E03847-000DomesticLifeInsuranceReportableSegments` → `DomesticLifeInsuranceReportableSegments`), matching `segments.py`'s `_clean_member_name()`. Avoids requiring every consumer to re-implement the cleaning.

### Deprecated

The deprecations below all emit `DeprecationWarning`. They will be removed in a future major release; consumers should migrate to the fact-shaped equivalents.

- **`Entity.is_listed`** — use `entity.entity_type == EntityType.LISTED_COMPANY`.
- **`Entity.is_fund_issuer`** — use `entity.entity_type == EntityType.FUND`.
- **`EntityClassifier.is_listed(edinet_code)`** — use `classifier.get_entity_type(code) == EntityType.LISTED_COMPANY`.
- **`TreasuryStockReport.has_board_authorization`** — use `bool(parsed.by_board_meeting and parsed.by_board_meeting.strip())` directly.
- **`TreasuryStockReport.has_shareholder_authorization`** — use `bool(parsed.by_shareholders_meeting and parsed.by_shareholders_meeting.strip())` directly.
- **`utils.process_zip_directory()`** — use `extract_csv_from_zip()` for in-memory CSV extraction or `extract_csv_to_disk()` for disk output (both in `edinet_tools.parsers.extraction`).
- **All public methods on `EdinetClient`** (`get_documents_by_date`, `get_recent_filings`, `get_company_filings`, `search_companies`, `download_filing_raw`, `download_filing`, `download_filings_batch`, `extract_filing_data`) — use the module-level functions and `Document` / `Entity` classes instead. Migration paths are named in each method's `DeprecationWarning` message.

### Removed

- **`ExtraordinaryReport.is_fund` / `SemiAnnualReport.is_fund`** and the intermediate `filer_namespace` field — replaced by registry-based classification via `report.filer.entity_type`.
- **`parsers.namespace_helpers`** (`infer_filer_type()`) — namespace inference conflated the shared `jppfs_cor:` taxonomy with corporate-only signal; parsers now expose facts, consumers classify via the FSA registry.
- **`parser.extract_mtp_targets()`** — dead code, zero callers.

### Tests

- Audit-closure remediation across routing / processor / API test families (real-ZIP body-execution assertions, dead-fixture removal).
- Real-EDINET golden fixtures per failure class (segments incl. no-anchor, consolidated-revenue, blast-radius characterization).
- Test count: 612 → 798.

## v0.6.0 — 2026-05-12

### Added

- `normalize_for_matching(s)` — public name-matching helper. NFKC normalization, `(株)` → `株式会社` / `(有)` → `有限会社` rewrites, katakana / Latin middle-dot stripping (`・` U+30FB, `·` U+00B7), whitespace collapse (runs folded to a single ASCII space; whitespace preserved between words so `Toyota` doesn't match `Toyo Tanso`), lowercase. Idempotent.
- `entity_by_corporate_number(num)` — O(1) lookup by 13-digit 法人番号 (Japan Corporate Number).
- `Entity.name_phonetic` and `Entity.corporate_number` now populated for classifier-path entities. Sourced from the `Submitter Name (phonetic)` and `Submitter's Japan Corporate Number` columns of `EdinetcodeDlInfo.csv`.
- GitHub Actions CI workflow (`.github/workflows/test.yml`) — multi-Python test matrix on push and pull_request.

### Changed

- `search_entities()` — O(1) exact-match via reverse index; substring-fallback path uses pre-normalized forms on both sides. Visually-identical strings with different Unicode encodings (full-width vs half-width Latin, `（` vs `(`, `㈱` vs `株式会社`, middle-dot variants like `モルガン・スタンレー` vs `モルガンスタンレー`) now resolve to the same entity.
- `search_entities()` bidirectional whitespace handling — when a query like `山田太郎` doesn't exact-match, falls back to the whitespace-collapsed catalog form, recovering names where the catalog stores them with internal spaces (`山田 太郎`). Particularly relevant for Japanese individual-filer names.
- `entity_by_ticker()` — O(N) scan replaced with O(1) reverse-index lookup. Now also handles alphanumeric tickers (`192A`, `263A`, `275A`-class).

### Not changed

- Public API signatures and return shapes — drop-in upgrade for existing callers.

### Known limitations (documented as xfail tests)

- Punctuation / symbol / abbreviation variance (`Co Ltd` ↔ `Co., Ltd.`, `&` ↔ `and`, `Inc` ↔ `Incorporated`).
- Queries with trailing parentheticals longer than the catalog name (e.g. `(信託口)` trust-account suffixes) — downstream consumers needing this should pre-strip before calling `search_entities`.
- Trust banks (`日本マスタートラスト信託銀行` etc.) are not in the EDINET catalog at all — they exist in the 法人番号 corporate registry only. v0.7.0+ may add a `法人番号公表サイト` ingestion layer to cover them.

## v0.5.1

- More robust EN/JP catalog loader — resolves columns by header alias, accepts both Japanese and English variants of FSA's `EdinetcodeDlInfo.csv` and `FundcodeDlInfo.csv`, fails loudly on schema renames.
- Fund-precedence fix in `EntityClassifier` — listed-company status now wins over fund-registry membership (Credit Saison, JAFCO etc. no longer misclassified as funds).
- Industry translation — `industry` field normalized to English regardless of CSV variant; raw Japanese preserved separately. New `translate_industry_to_english()` public helper.
- `scripts/refresh_csvs.py` — downloads fresh CSVs from FSA.
- CSVs refreshed.

## v0.5.0

Typed parsers for all 42 EDINET document types.

## v0.4.3

Add `fetch_and_parse` API. Expose `industry` field on `Entity`.
