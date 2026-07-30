"""
EDINET Tools - Python package for accessing Japanese corporate financial data.

Python library for Japanese financial disclosure data.
"""

__version__ = "0.7.1"
__author__ = "Matt Helmer"
__description__ = "Python package for accessing Japanese corporate financial data from EDINET"

# Core API
from ._client import configure, documents, fetch_and_parse
from .client import EdinetClient  # Deprecated, but kept for migration
from .config import SUPPORTED_DOC_TYPES as DOCUMENT_TYPES
from .doc_types import DocType, doc_type, doc_types, list_doc_types
from .document import Document

# Entity-first API
from .entity import (
    Entity,
    Fund,
    entity,
    entity_by_code,  # Shorter alias
    entity_by_corporate_number,
    entity_by_edinet_code,
    entity_by_ticker,
    fund,
    funds_by_issuer,
    search,
    search_entities,
)

# Entity classification
from .entity_classifier import EntityClassifier, EntityType
from .normalize import normalize_for_matching

# Parsers
from .parsers import (
    ConfirmationReport,
    ExtraordinaryReport,
    GenericReport,  # Backwards compatibility alias
    InternalControlReport,
    LargeHoldingChangeReport,
    LargeHoldingReport,
    ParentCompanyReport,
    ParsedReport,
    QuarterlyReport,
    RawReport,
    SecuritiesReport,
    SemiAnnualReport,
    TenderOfferReport,
    TreasuryStockReport,
    parse,
    supported_doc_types,
)
from .timezone import today_jst

__all__ = [
    "DOCUMENT_TYPES",
    "ConfirmationReport",
    "DocType",
    "Document",
    "EdinetClient",
    "Entity",
    "EntityClassifier",
    "EntityType",
    "ExtraordinaryReport",
    "Fund",
    "GenericReport",
    "InternalControlReport",
    "LargeHoldingChangeReport",
    "LargeHoldingReport",
    "ParentCompanyReport",
    "ParsedReport",
    "QuarterlyReport",
    "RawReport",
    "SecuritiesReport",
    "SemiAnnualReport",
    "TenderOfferReport",
    "TreasuryStockReport",
    "__version__",
    "configure",
    "doc_type",
    "doc_types",
    "documents",
    "entity",
    "entity_by_code",
    "entity_by_corporate_number",
    "entity_by_edinet_code",
    "entity_by_ticker",
    "fetch_and_parse",
    "fund",
    "funds_by_issuer",
    "list_doc_types",
    "normalize_for_matching",
    "parse",
    "search",
    "search_entities",
    "supported_doc_types",
    "today_jst",
]
