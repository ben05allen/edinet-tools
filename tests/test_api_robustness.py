"""Tests for API robustness: retry classification, filename sanitization,
and JSON error body detection.

These tests surface three flaws identified in code review:
- Flaw 3:  Retry logic retries ALL errors including deterministic 4xx
- Flaw 6:  download_documents doesn't sanitize filenames from API data
- Flaw 10: Dead non-200 check; missing JSON error body detection for 200 responses
"""

import json
import os
import urllib.error
from email.message import Message
from unittest.mock import Mock, patch

import pytest

from edinet_tools.api import (
    fetch_document,
    fetch_documents_list,
    download_documents,
)


def _http_error(
    code: int,
    msg: str,
    url: str = "https://example.com",
    body: bytes = b"",
    hdrs: Message | None = None,
) -> urllib.error.HTTPError:
    """Helper to construct an HTTPError with correct types."""
    return urllib.error.HTTPError(
        url=url,
        code=code,
        msg=msg,
        hdrs=hdrs or Message(),
        fp=Mock(read=Mock(return_value=body)),
    )


# ─── Flaw 3: Retry classification ───────────────────────────────────────────


class TestRetryClassification:
    """Verify that deterministic client errors are NOT retried,
    while transient server errors and rate limits ARE retried."""

    @patch("edinet_tools.api.time.sleep")
    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_401_not_retried(self, mock_urlopen, mock_sleep):
        """401 Unauthorized should fail immediately — no retries."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com",
            code=401,
            msg="Unauthorized",
            hdrs=Message(),
            fp=Mock(read=Mock(return_value=b'{"message": "Invalid key"}')),
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            fetch_documents_list("2025-01-15", max_retries=3, api_key="bad-key")

        assert exc_info.value.code == 401
        # Should have been called only once (no retries)
        assert mock_urlopen.call_count == 1
        mock_sleep.assert_not_called()

    @patch("edinet_tools.api.time.sleep")
    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_404_not_retried(self, mock_urlopen, mock_sleep):
        """404 Not Found should fail immediately — no retries."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=Mock(read=Mock(return_value=b'{"message": "Not found"}')),
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            fetch_documents_list("2025-01-15", max_retries=3)

        assert exc_info.value.code == 404
        assert mock_urlopen.call_count == 1
        mock_sleep.assert_not_called()

    @patch("edinet_tools.api.time.sleep")
    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_500_retried_then_fails(self, mock_urlopen, mock_sleep):
        """500 Internal Server Error should be retried, then fail on last attempt."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs=Message(),
            fp=Mock(read=Mock(return_value=b"Server error")),
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            fetch_documents_list("2025-01-15", max_retries=3)

        assert exc_info.value.code == 500
        # Should have retried twice (attempt 1 fails, attempt 2 fails, attempt 3 fails = 3 calls)
        assert mock_urlopen.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("edinet_tools.api.time.sleep")
    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_500_retries_succeed(self, mock_urlopen, mock_sleep):
        """500 on first attempt, success on second — should succeed."""
        error = urllib.error.HTTPError(
            url="https://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs=Message(),
            fp=Mock(read=Mock(return_value=b"Server error")),
        )
        success_response = Mock()
        success_response.read.return_value = b'{"results": []}'
        success_response.__enter__ = Mock(return_value=success_response)
        success_response.__exit__ = Mock(return_value=False)

        mock_urlopen.side_effect = [error, success_response]

        result = fetch_documents_list("2025-01-15", max_retries=3)

        assert result == {"results": []}
        assert mock_urlopen.call_count == 2
        mock_sleep.assert_called_once()

    @patch("edinet_tools.api.time.sleep")
    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_429_retried_with_retry_after(self, mock_urlopen, mock_sleep):
        """429 Rate Limit should be retried."""
        hdrs = Message()
        hdrs["Retry-After"] = "5"
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com",
            code=429,
            msg="Too Many Requests",
            hdrs=hdrs,
            fp=Mock(read=Mock(return_value=b"Rate limited")),
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            fetch_documents_list("2025-01-15", max_retries=3)

        assert exc_info.value.code == 429
        assert mock_urlopen.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("edinet_tools.api.time.sleep")
    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_fetch_document_401_not_retried(self, mock_urlopen, mock_sleep):
        """fetch_document should also not retry 401 errors."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com",
            code=401,
            msg="Unauthorized",
            hdrs=Message(),
            fp=Mock(read=Mock(return_value=b'{"message": "Invalid key"}')),
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            fetch_document("S100ABC", max_retries=3, api_key="bad-key")

        assert exc_info.value.code == 401
        assert mock_urlopen.call_count == 1
        mock_sleep.assert_not_called()


# ─── Flaw 6: Filename sanitization ──────────────────────────────────────────


class TestFilenameSanitization:
    """Verify that download_documents sanitizes filenames derived from API data."""

    @patch("edinet_tools.api.fetch_document")
    @patch("edinet_tools.api.save_document_content")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_slash_in_filer_name(self, mock_makedirs, mock_exists, mock_save, mock_fetch):
        """A filer name containing '/' must not create subdirectories."""
        mock_exists.return_value = False
        mock_fetch.return_value = b"content"

        docs = [
            {"docID": "S100A001", "docTypeCode": "160", "filerName": "Company/With/Slashes"},
        ]

        download_documents(docs, download_dir="/tmp/dl")

        save_path = mock_save.call_args[0][1]
        # The path should be a single flat file, no subdirectories
        assert save_path.count("/") == "/tmp/dl/".count("/")
        assert "Company_With_Slashes" in save_path or "Company" in save_path

    @patch("edinet_tools.api.fetch_document")
    @patch("edinet_tools.api.save_document_content")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_backslash_in_filer_name(self, mock_makedirs, mock_exists, mock_save, mock_fetch):
        """A filer name containing '\\' must be sanitized."""
        mock_exists.return_value = False
        mock_fetch.return_value = b"content"

        docs = [
            {"docID": "S100A001", "docTypeCode": "160", "filerName": "Company\\Backslash"},
        ]

        download_documents(docs, download_dir="/tmp/dl")

        save_path = mock_save.call_args[0][1]
        assert "\\\\" not in save_path  # No raw backslashes in path

    @patch("edinet_tools.api.fetch_document")
    @patch("edinet_tools.api.save_document_content")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_colon_in_filer_name(self, mock_makedirs, mock_exists, mock_save, mock_fetch):
        """A filer name containing ':' must be sanitized."""
        mock_exists.return_value = False
        mock_fetch.return_value = b"content"

        docs = [
            {"docID": "S100A001", "docTypeCode": "160", "filerName": "Company:Colon"},
        ]

        download_documents(docs, download_dir="/tmp/dl")

        save_path = mock_save.call_args[0][1]
        filename = os.path.basename(save_path)
        assert ":" not in filename

    @patch("edinet_tools.api.fetch_document")
    @patch("edinet_tools.api.save_document_content")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_long_filer_name_truncated(self, mock_makedirs, mock_exists, mock_save, mock_fetch):
        """A very long filer name must be truncated to fit filesystem limits."""
        mock_exists.return_value = False
        mock_fetch.return_value = b"content"

        long_name = "A" * 300
        docs = [
            {"docID": "S100A001", "docTypeCode": "160", "filerName": long_name},
        ]

        download_documents(docs, download_dir="/tmp/dl")

        save_path = mock_save.call_args[0][1]
        filename = os.path.basename(save_path)
        # Total filename should be well under 255 bytes
        assert len(filename.encode("utf-8")) <= 255

    @patch("edinet_tools.api.fetch_document")
    @patch("edinet_tools.api.save_document_content")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_normal_filer_name_preserved(self, mock_makedirs, mock_exists, mock_save, mock_fetch):
        """Normal filer names should be preserved (just truncated if too long)."""
        mock_exists.return_value = False
        mock_fetch.return_value = b"content"

        docs = [
            {"docID": "S100A001", "docTypeCode": "160", "filerName": "Toyota Motor Corporation"},
        ]

        download_documents(docs, download_dir="/tmp/dl")

        save_path = mock_save.call_args[0][1]
        assert "Toyota Motor Corporation" in save_path
        assert save_path.endswith(".zip")


# ─── Flaw 10: JSON error body detection ─────────────────────────────────────


class TestJsonErrorBodyDetection:
    """The EDINET API sometimes returns HTTP 200 with a JSON error body
    (e.g. `{"metadata": {"status": "404", "message": "..."}}`).
    These tests verify that such responses are detected and raise errors
    rather than being returned as valid data."""

    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_fetch_list_json_error_not_returned_as_data(self, mock_urlopen):
        """A 200 response with error JSON should not be returned as valid data."""
        error_body = json.dumps(
            {
                "metadata": {
                    "status": "404",
                    "message": "Document not found",
                    "resultset": {"count": 0},
                },
                "results": None,
            }
        ).encode("utf-8")

        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = error_body
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Should raise an error, not return the error JSON as valid data
        with pytest.raises(Exception) as exc_info:
            fetch_documents_list("2025-01-15", max_retries=1)

        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_fetch_document_json_error_not_returned_as_bytes(self, mock_urlopen):
        """A 200 response with error JSON should not be returned as document bytes."""
        error_body = json.dumps(
            {
                "metadata": {
                    "status": "404",
                    "message": "Document not found",
                },
            }
        ).encode("utf-8")

        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = error_body
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            fetch_document("S100INVALID", max_retries=1)

        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    @patch("edinet_tools.api.urllib.request.urlopen")
    @patch("edinet_tools.api.EDINET_API_KEY", "test-key")
    def test_fetch_list_valid_200_not_rejected(self, mock_urlopen):
        """A legitimate 200 response with valid data should work fine."""
        valid_body = json.dumps(
            {
                "metadata": {"status": "200", "message": "OK"},
                "results": [{"docID": "S100ABC"}],
            }
        ).encode("utf-8")

        mock_response = Mock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = valid_body
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_documents_list("2025-01-15", max_retries=1)
        assert result["results"][0]["docID"] == "S100ABC"
