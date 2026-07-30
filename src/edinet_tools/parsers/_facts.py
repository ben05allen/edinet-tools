"""
Fact dataclass — preserves every (element_id, context_id, value, unit_id) triple.

Additive complement to the existing raw_fields dict (which is last-wins by
element_id). raw_facts preserves multi-context triples for parsers that
need cross-context data (e.g., multi-period segments in v0.7.0, 5-yr
financial history in a later release).

Per spec §4.3: existing raw_fields behavior unchanged.
"""

from dataclasses import dataclass


@dataclass
class Fact:
    """A single XBRL fact: (element_id, context_id, value, unit_id)."""

    element_id: str
    context_id: str
    value: str
    unit_id: str | None = None
