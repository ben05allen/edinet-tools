"""Tests for the public disk-write helpers added in v0.6.1."""

import io
import zipfile
from pathlib import Path


from edinet_tools.parsers.extraction import extract_csv_to_disk


def _make_test_zip(csv_content: str, csv_name: str = "jpcrp030000-asr-001_test.csv") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"XBRL_TO_CSV/{csv_name}", csv_content.encode("utf-16-le"))
    return buf.getvalue()


def _sample_csv_content() -> str:
    # Note: extractor parses all rows as data, so we omit the literal header line
    row1 = "\t".join(
        [
            "jpdei_cor:EDINETCodeDEI",
            "EDINETコード、DEI",
            "FilingDateInstant",
            "提出日時点",
            "その他",
            "時点",
            "",
            "",
            "E12345",
        ]
    )
    row2 = "\t".join(
        [
            "jpcrp_cor:NetSales",
            "売上高",
            "CurrentYearDuration",
            "当期",
            "連結",
            "期間",
            "JPY",
            "円",
            "1000000000",
        ]
    )
    return "\n".join([row1, row2])


def test_extract_csv_to_disk_writes_files(tmp_path):
    zip_bytes = _make_test_zip(_sample_csv_content())
    paths = extract_csv_to_disk(zip_bytes, tmp_path)
    assert len(paths) == 1
    assert paths[0].exists()
    assert paths[0].suffix == ".csv"


def test_extract_csv_to_disk_returns_paths_as_path_objects(tmp_path):
    zip_bytes = _make_test_zip(_sample_csv_content())
    paths = extract_csv_to_disk(zip_bytes, tmp_path)
    assert all(isinstance(p, Path) for p in paths)


def test_extract_csv_to_disk_creates_output_dir_if_missing(tmp_path):
    target = tmp_path / "new_subdir" / "nested"
    assert not target.exists()
    zip_bytes = _make_test_zip(_sample_csv_content())
    paths = extract_csv_to_disk(zip_bytes, target)
    assert target.exists()
    assert len(paths) == 1


def test_extract_csv_to_disk_preserves_9_column_shape(tmp_path):
    zip_bytes = _make_test_zip(_sample_csv_content())
    paths = extract_csv_to_disk(zip_bytes, tmp_path)
    content = paths[0].read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 3  # written header + 2 data rows
    for line in lines:
        cols = line.split("\t")
        assert len(cols) == 9, f"Expected 9 columns, got {len(cols)}: {cols}"


def test_extract_csv_to_disk_returns_empty_list_for_zip_with_no_csvs(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("XBRL_TO_CSV/readme.txt", b"no csvs here")
    paths = extract_csv_to_disk(buf.getvalue(), tmp_path)
    assert paths == []


def test_extract_csv_to_disk_accepts_string_path(tmp_path):
    zip_bytes = _make_test_zip(_sample_csv_content())
    paths = extract_csv_to_disk(zip_bytes, str(tmp_path))
    assert len(paths) == 1
    assert paths[0].exists()


def test_document_save_extracted_csvs(monkeypatch, tmp_path):
    """Document.save_extracted_csvs() fetches (if needed) then writes to disk."""
    from edinet_tools.document import Document

    zip_bytes = _make_test_zip(_sample_csv_content())
    doc = Document(
        {
            "docID": "S100TEST",
            "docTypeCode": "120",
            "edinetCode": "E12345",
            "filerName": "Test Co",
            "submitDateTime": "2026-05-21 09:00",
        }
    )
    monkeypatch.setattr(doc, "fetch", lambda: zip_bytes)

    paths = doc.save_extracted_csvs(tmp_path)
    assert len(paths) == 1
    assert paths[0].exists()
    assert paths[0].suffix == ".csv"
