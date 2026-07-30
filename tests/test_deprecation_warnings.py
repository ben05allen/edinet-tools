"""Tests asserting deprecated methods emit DeprecationWarning with migration paths."""

import warnings

import pytest

from edinet_tools.client import EdinetClient


@pytest.fixture
def client():
    return EdinetClient(api_key="test-key-not-real")


@pytest.mark.parametrize(
    "method_name,expected_replacement_keyword",
    [
        ("get_documents_by_date", "documents"),
        ("get_recent_filings", "documents"),
        ("get_company_filings", "Entity.documents"),
        ("download_filing_raw", "Document.fetch"),
        ("download_filing", "Document.parse"),
        ("download_filings_batch", "Document.fetch"),
        ("extract_filing_data", "parsers.parse"),
        ("search_companies", "search_entities"),
    ],
)
def test_method_emits_deprecation_warning_with_replacement(
    client, method_name, expected_replacement_keyword
):
    method = getattr(client, method_name, None)
    if method is None:
        pytest.skip(f"{method_name} not on EdinetClient — adjust the test parametrization")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            method()
        except Exception:  # noqa: BLE001, S110 — test only checks warning emission, not call success
            pass

        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1, f"{method_name} did not emit DeprecationWarning"
        msg = str(dep_warnings[0].message)
        assert method_name in msg, f"warning for {method_name} did not name the method: {msg}"
        assert expected_replacement_keyword in msg, (
            f"warning for {method_name} did not point to replacement '{expected_replacement_keyword}': {msg}"
        )


def test_process_zip_directory_emits_deprecation_warning(tmp_path):
    """utils.process_zip_directory() is deprecated in favor of modular CSV helpers."""
    from edinet_tools.utils import process_zip_directory

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            process_zip_directory(str(tmp_path))
        except Exception:  # noqa: BLE001, S110 — test only checks warning emission, not call success
            pass

        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1
        msg = str(dep_warnings[0].message)
        assert "process_zip_directory" in msg
        assert "extract_csv_from_zip" in msg or "extract_csv_to_disk" in msg


def test_entity_is_listed_emits_deprecation_warning():
    """Entity.is_listed is deprecated in v0.6.1; use entity_type."""
    from edinet_tools.entity import Entity

    entity = Entity({"edinet_code": "E00001", "is_listed": True})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = entity.is_listed
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1
        msg = str(dep_warnings[0].message)
        assert "is_listed" in msg
        assert "entity_type" in msg


def test_entity_is_fund_issuer_emits_deprecation_warning():
    """Entity.is_fund_issuer is deprecated in v0.6.1; use entity_type."""
    from edinet_tools.entity import Entity

    entity = Entity({"edinet_code": "E00001"})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = entity.is_fund_issuer
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1
        msg = str(dep_warnings[0].message)
        assert "is_fund_issuer" in msg
        assert "entity_type" in msg


def test_entity_classifier_is_listed_emits_deprecation_warning():
    """EntityClassifier.is_listed() is deprecated in v0.6.1; use get_entity_type()."""
    from edinet_tools.entity_classifier import EntityClassifier

    classifier = EntityClassifier()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            classifier.is_listed("E00001")
        except Exception:  # noqa: BLE001, S110 — test only checks warning emission, not call success
            pass
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep_warnings) >= 1
        msg = str(dep_warnings[0].message)
        assert "is_listed" in msg
        assert "get_entity_type" in msg


def test_entity_entity_type_property_exists():
    """Entity.entity_type is the new public fact-shaped accessor."""
    from edinet_tools.entity import Entity
    from edinet_tools.entity_classifier import EntityType

    entity = Entity({"edinet_code": "E_NONEXISTENT"})
    result = entity.entity_type
    # Returns an EntityType enum value (UNKNOWN for non-existent codes)
    assert result == EntityType.UNKNOWN
