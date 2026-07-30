"""Test that parse functions accept pre-extracted csv_files."""

import unittest
from unittest.mock import MagicMock

from edinet_tools.parsers.extraordinary import ExtraordinaryReport, parse_extraordinary_report
from edinet_tools.parsers.large_holding import LargeHoldingReport, parse_large_holding
from edinet_tools.parsers.quarterly import QuarterlyReport, parse_quarterly_report
from edinet_tools.parsers.securities import SecuritiesReport, parse_securities_report
from edinet_tools.parsers.semi_annual import SemiAnnualReport, parse_semi_annual_report
from edinet_tools.parsers.tender_offer import TenderOfferReport, parse_tender_offer
from edinet_tools.parsers.treasury_stock import TreasuryStockReport, parse_treasury_stock_report


class TestCsvFilesParameter(unittest.TestCase):
    """All parse functions should accept csv_files kwarg and not crash on document=None."""

    def _empty_csv(self):
        return [{"filename": "test.csv", "data": []}]

    def test_parse_large_holding_with_csv_files(self):
        result = parse_large_holding(
            document=None, csv_files=self._empty_csv(), doc_id="S100TEST", doc_type_code="350"
        )
        self.assertIsInstance(result, LargeHoldingReport)
        self.assertEqual(result.doc_id, "S100TEST")
        self.assertEqual(result.doc_type_code, "350")

    def test_parse_securities_report_with_csv_files(self):
        result = parse_securities_report(
            document=None, csv_files=self._empty_csv(), doc_id="S100TEST", doc_type_code="120"
        )
        self.assertIsInstance(result, SecuritiesReport)
        self.assertEqual(result.doc_id, "S100TEST")

    def test_parse_extraordinary_report_with_csv_files(self):
        result = parse_extraordinary_report(
            document=None, csv_files=self._empty_csv(), doc_id="S100TEST", doc_type_code="180"
        )
        self.assertIsInstance(result, ExtraordinaryReport)
        self.assertEqual(result.doc_id, "S100TEST")

    def test_parse_treasury_stock_report_with_csv_files(self):
        result = parse_treasury_stock_report(
            document=None, csv_files=self._empty_csv(), doc_id="S100TEST", doc_type_code="220"
        )
        self.assertIsInstance(result, TreasuryStockReport)
        self.assertEqual(result.doc_id, "S100TEST")

    def test_parse_semi_annual_report_with_csv_files(self):
        result = parse_semi_annual_report(
            document=None, csv_files=self._empty_csv(), doc_id="S100TEST", doc_type_code="160"
        )
        self.assertIsInstance(result, SemiAnnualReport)
        self.assertEqual(result.doc_id, "S100TEST")

    def test_parse_tender_offer_with_csv_files(self):
        result = parse_tender_offer(
            document=None, csv_files=self._empty_csv(), doc_id="S100TEST", doc_type_code="240"
        )
        self.assertIsInstance(result, TenderOfferReport)
        self.assertEqual(result.doc_id, "S100TEST")

    def test_parse_quarterly_report_with_csv_files(self):
        result = parse_quarterly_report(
            document=None, csv_files=self._empty_csv(), doc_id="S100TEST", doc_type_code="140"
        )
        self.assertIsInstance(result, QuarterlyReport)
        self.assertEqual(result.doc_id, "S100TEST")


class TestDocumentPathStillWorks(unittest.TestCase):
    """Existing document-based call path must not regress."""

    @staticmethod
    def _minimal_valid_zip():
        """ZIP with one CSV row carrying jpdei_cor:EDINETCodeDEI=E99999.
        Lets the parser body actually execute past the empty-input short-circuit."""
        import io
        import zipfile

        buf = io.BytesIO()
        csv_body = (
            "\t".join(  # noqa: FLY002 — list-join is clearer for TSV rows
                [
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
            )
            + "\n"
            + "\t".join(  # noqa: FLY002 — list-join is clearer for TSV rows
                [
                    "jpdei_cor:EDINETCodeDEI",
                    "EDINETコード",
                    "FilingDateInstant",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "E99999",
                ]
            )
            + "\n"
        )
        # Use UTF-16-LE BOM-prefixed encoding — what EDINET ships and what
        # extract_csv_from_zip auto-detects.
        encoded = b"\xff\xfe" + csv_body.encode("utf-16-le")
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("XBRL_TO_CSV/jpcrp030000-asr_test.csv", encoded)
        return buf.getvalue()

    def _mock_doc(self, doc_type="350"):
        mock = MagicMock()
        mock.doc_id = "S100TEST"
        mock.doc_type_code = doc_type
        mock.filer_name = "Test Corp"
        mock.filer_edinet_code = "E99999"
        mock.filing_datetime = None
        mock.fetch.return_value = self._minimal_valid_zip()
        return mock

    def test_large_holding_with_document(self):
        """parse_large_holding accepts a document positionally AND the parse body
        runs (proven by an extracted field landing on the result)."""
        result = parse_large_holding(self._mock_doc("350"))
        self.assertIsInstance(result, LargeHoldingReport)
        self.assertEqual(result.doc_id, "S100TEST")
        # raw_fields populated proves the CSV reached the parser body, not just
        # signature acceptance (the prior try/except: pass only guaranteed signature).
        self.assertEqual(result.raw_fields.get("jpdei_cor:EDINETCodeDEI"), "E99999")

    def test_securities_with_document(self):
        """parse_securities_report accepts a document positionally + parse body runs."""
        result = parse_securities_report(self._mock_doc("120"))
        self.assertIsInstance(result, SecuritiesReport)
        self.assertEqual(result.doc_id, "S100TEST")
        self.assertEqual(result.raw_fields.get("jpdei_cor:EDINETCodeDEI"), "E99999")
