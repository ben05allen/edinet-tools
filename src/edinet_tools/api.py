# edinet_tools.py
import datetime
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import EDINET_API_KEY, SUPPORTED_DOC_TYPES
from .exceptions import APIError

# Use module-specific logger
logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _is_json_error_response(body: bytes) -> str | None:
    """Detect EDINET JSON error bodies returned with HTTP 200.

    The EDINET API sometimes returns ``{"metadata": {"status": "404", ...}}`
    with a 200 status code.  Returns the error message string if the body is
    an error, or ``None`` if the body looks like valid data.
    """
    try:
        data = json.loads(body)
        status = str(data.get("metadata", {}).get("status", ""))
        if status and status != "200":
            return data.get("metadata", {}).get("message", f"API error {status}")
    except (json.JSONDecodeError, AttributeError, TypeError, UnicodeDecodeError):
        pass
    return None


def _sanitize_filename(name: str, max_length: int = 100) -> str:
    """Remove filesystem-unsafe characters and truncate *name*."""
    safe = re.sub(r'[/\\:*?"<>|\x00]', "_", name)
    return safe[:max_length]


# API interaction functions
def fetch_documents_list(
    date: str | datetime.date,
    type: int = 2,
    max_retries: int = 3,
    delay_seconds: int = 5,
    api_key: str | None = None,
    timeout: int = 60,
) -> dict:
    """
    Retrieve disclosure documents from EDINET API for a specified date with retries.

    Args:
        date: Date string ('YYYY-MM-DD') or datetime.date object.
        type: EDINET API type parameter (1=metadata only, 2=metadata+results).
        max_retries: Maximum number of retry attempts on failure.
        delay_seconds: Kept for backwards compatibility; retries now use
            exponential backoff (2s, 4s, 8s, ... capped at 30s).
        api_key: Optional API key override.
        timeout: Timeout in seconds for the HTTP request (default 60).
    """
    if isinstance(date, str):
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")  # noqa: DTZ007 — validation only, result unused
        except ValueError:
            raise ValueError("Invalid date string. Use format 'YYYY-MM-DD'")
        date_str = date
    elif isinstance(date, datetime.date):
        date_str = date.strftime("%Y-%m-%d")
    else:
        raise TypeError("Date must be 'YYYY-MM-DD' or datetime.date")

    url = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
    params = {
        "date": date_str,
        "type": type,  # '1' is metadata only; '2' is metadata and results
        "Subscription-Key": api_key or EDINET_API_KEY,
    }
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1} to fetch documents for {date_str}...")
            with urllib.request.urlopen(full_url, timeout=timeout) as response:
                data = response.read()

                # EDINET may return HTTP 200 with a JSON error body
                error_msg = _is_json_error_response(data)
                if error_msg:
                    raise APIError(f"EDINET API error for {date_str}: {error_msg}")

                logger.info(f"Successfully fetched documents for {date_str}.")
                return json.loads(data)

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP {e.code} fetching documents for {date_str}: {e.reason}")
            # 429 (rate limit) and 5xx (server errors) are retryable
            if (e.code == 429 or e.code >= 500) and attempt < max_retries - 1:
                backoff = min(2 ** (attempt + 1), 30)
                logger.warning(f"Retrying in {backoff}s...")
                time.sleep(backoff)
                continue
            # 4xx client errors (except 429) are deterministic — fail immediately
            raise
        except urllib.error.URLError as e:
            logger.error(f"URL Error fetching documents for {date_str}: {e}")
            if attempt < max_retries - 1:
                backoff = min(2 ** (attempt + 1), 30)
                logger.warning(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                logger.error("Max retries reached for fetching documents.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error fetching documents for {date_str}: {e}")
            if attempt < max_retries - 1:
                backoff = min(2 ** (attempt + 1), 30)
                logger.warning(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                raise

    raise APIError("Failed to fetch documents after multiple retries.")


def fetch_document(
    doc_id: str,
    type: int = 5,
    max_retries: int = 3,
    delay_seconds: int = 5,
    api_key: str | None = None,
    timeout: int = 60,
) -> bytes:
    """
    Retrieve a specific document from EDINET API with retries and return raw bytes.

    Args:
        doc_id: EDINET document ID (e.g. 'S100ABC').
        type: EDINET document type to retrieve (default 5):
            1 = ZIP with HTML documents (PublicDoc, AuditDoc)
            2 = PDF
            3 = ZIP with attachments (AttachDoc)
            4 = ZIP with English documents (EnglishDoc)
            5 = XBRL to CSV (default, used by parsers)
        max_retries: Maximum number of retry attempts on failure.
        delay_seconds: Kept for backwards compatibility; retries now use
            exponential backoff (2s, 4s, 8s, ... capped at 30s).
        api_key: Optional API key override.
        timeout: Timeout in seconds for the HTTP request (default 60).
    """
    url = f"https://disclosure.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
    params = {
        "type": type,
        "Subscription-Key": api_key or EDINET_API_KEY,
    }
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1} to fetch document {doc_id}...")
            with urllib.request.urlopen(full_url, timeout=timeout) as response:
                content = response.read()

                # EDINET may return HTTP 200 with a JSON error body
                error_msg = _is_json_error_response(content)
                if error_msg:
                    raise APIError(f"EDINET API error for {doc_id}: {error_msg}")

                logger.info(f"Successfully fetched document {doc_id}.")
                return content

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP {e.code} fetching document {doc_id}: {e.reason}")
            if (e.code == 429 or e.code >= 500) and attempt < max_retries - 1:
                backoff = min(2 ** (attempt + 1), 30)
                logger.warning(f"Retrying in {backoff}s...")
                time.sleep(backoff)
                continue
            raise
        except urllib.error.URLError as e:
            logger.error(f"URL Error fetching document {doc_id}: {e}")
            if attempt < max_retries - 1:
                backoff = min(2 ** (attempt + 1), 30)
                logger.warning(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                logger.error("Max retries reached for fetching document.")
                raise
        except Exception as e:
            logger.error(f"Unexpected error fetching document {doc_id}: {e}")
            if attempt < max_retries - 1:
                backoff = min(2 ** (attempt + 1), 30)
                logger.warning(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                raise

    raise APIError(f"Failed to fetch document {doc_id} after multiple retries.")


def save_document_content(doc_content: bytes, output_path: str) -> None:
    """Save the document content (bytes) to file."""
    try:
        with open(output_path, "wb") as file_out:
            file_out.write(doc_content)
        logger.info(f"Saved document content to {output_path}")
    except OSError as e:
        logger.error(f"Error saving document content to {output_path}: {e}")
        raise  # Re-raise to indicate failure


def download_documents(docs: list[dict], download_dir: str = "./downloads") -> None:
    """
    Download all documents in the provided list.
    """
    os.makedirs(download_dir, exist_ok=True)
    logger.info(f"Ensured download directory exists: {download_dir}")

    total_docs = len(docs)
    logger.info(f"Starting download of {total_docs} documents.")

    for i, doc in enumerate(docs, 1):
        doc_id = doc.get("docID")
        doc_type_code = doc.get("docTypeCode")
        filer = doc.get("filerName")

        if not doc_id or not doc_type_code or not filer:
            logger.warning(f"Skipping document {i}/{total_docs} due to missing metadata: {doc}")
            continue

        save_name = f"{doc_id}-{doc_type_code}-{_sanitize_filename(filer)}.zip"
        output_path = os.path.join(download_dir, save_name)

        logger.info(f"Downloading {i}/{total_docs}: `{save_name}`")

        if not os.path.exists(output_path):
            try:
                # make GET request to `documents/{docID}` endpoint
                doc_content = fetch_document(doc_id)
                save_document_content(doc_content, output_path)
            except (OSError, APIError) as e:
                logger.error(f"Error downloading and saving {save_name}: {e}")
        else:
            # logger.info(f"File already exists: {save_name}")
            pass  # Keep this silent unless debugging needed

    logger.info(f"Download process complete. Files saved to: `{download_dir}`")


# Document filtering and processing
def filter_documents(
    docs: list[dict],
    edinet_codes: list[str] | str | None = None,
    doc_type_codes: list[str] | str | None = None,
    excluded_doc_type_codes: list[str] | str | None = None,
    require_sec_code: bool = True,
) -> list[dict]:
    """Filter list of documents by EDINET codes and document type codes."""
    if edinet_codes is None:
        edinet_codes = []
    if doc_type_codes is None:
        doc_type_codes = []
    if excluded_doc_type_codes is None:
        excluded_doc_type_codes = []
    if isinstance(edinet_codes, str):
        edinet_codes = [edinet_codes]
    if isinstance(doc_type_codes, str):
        doc_type_codes = [doc_type_codes]
    if isinstance(excluded_doc_type_codes, str):
        excluded_doc_type_codes = [excluded_doc_type_codes]

    filtered_list = []
    for doc in docs:
        # Basic checks
        if "docID" not in doc or "docTypeCode" not in doc or "filerName" not in doc:
            logger.warning(f"Skipping document with incomplete metadata: {doc}")
            continue

        # Check for supported document types (optional, but good practice)
        if doc["docTypeCode"] not in SUPPORTED_DOC_TYPES:
            # logger.debug(f"Skipping document type {doc['docTypeCode']} ({doc['filerName']}) - not supported.")
            continue  # Skip document types we don't explicitly support analysis for

        # Apply EDINET code filter
        if edinet_codes and doc.get("edinetCode") not in edinet_codes:
            continue

        # Apply document type code filter
        if doc_type_codes and doc["docTypeCode"] not in doc_type_codes:
            continue

        # Apply excluded document type code filter
        if doc["docTypeCode"] in excluded_doc_type_codes:
            continue

        # Apply require securities code filter
        if require_sec_code and doc.get("secCode") is None:
            continue

        filtered_list.append(doc)

    logger.info(
        f"Filtered down to {len(filtered_list)} documents from initial list of {len(docs)}."
    )
    return filtered_list


def get_documents_for_date_range(
    start_date: datetime.date,
    end_date: datetime.date,
    edinet_codes: list[str] | None = None,
    doc_type_codes: list[str] | None = None,
    excluded_doc_type_codes: list[str] | None = None,
    require_sec_code: bool = True,
    api_key: str | None = None,
) -> list[dict]:
    """Retrieve and filter documents for a date range."""
    matching_docs = []
    current_date = start_date
    while current_date <= end_date:
        try:
            docs_res = fetch_documents_list(date=current_date, api_key=api_key)
            if docs_res and docs_res.get("results"):
                logger.info(
                    f"Found {len(docs_res['results'])} documents on EDINET for {current_date}."
                )
                filtered_docs = filter_documents(
                    docs_res["results"],
                    edinet_codes,
                    doc_type_codes,
                    excluded_doc_type_codes,
                    require_sec_code,
                )
                matching_docs.extend(filtered_docs)
                logger.info(f"Added {len(filtered_docs)} matching documents for {current_date}.")
            elif docs_res and docs_res.get("results") is None:
                logger.info(f"No documents listed for {current_date}.")
            elif not docs_res:
                logger.warning(f"Empty response received for {current_date}.")

        except (OSError, APIError) as e:
            logger.error(f"Error processing documents for date {current_date}: {e}")
            # Continue to next date even if one date fails
        finally:
            current_date += datetime.timedelta(days=1)

    logger.info(
        f"Finished retrieving documents for date range. Total matching documents: {len(matching_docs)}"
    )
    return matching_docs
