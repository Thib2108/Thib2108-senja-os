"""Facet contracts — from the knowledge-axis taxonomy (SKOS/PROV-O anchored).

TODO(gen): FacetScheme + per-scheme value enums are generated from the taxonomy
pages, same pattern as edges.py. Hand-written vocabulary is a CI failure.
"""

from enum import StrEnum


class TagSource(StrEnum):
    """Facts, decisions, and derived values never mix (004 Principle 2).

    Auto-classifiers NEVER overwrite declared/locked values.
    """

    AUTO = "auto"
    RECORDED = "recorded"
    DECLARED = "declared"
    DERIVED = "derived"
    INHERITED = "inherited"


# Gauntlet-at-registration (004 ADR-05): these block registration when absent.
MIN_VIABLE_TAG_SET: tuple[str, ...] = ("genre", "topic", "sensitivity")
