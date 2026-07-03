"""Typed I/O for the knowledge pipelines — SDAI-CHAT-004 Block 5.

Enums come from packages/contracts (generated from taxonomies + Edge Registry);
hand-written vocabulary here is a CI failure.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from contracts.edges import Provenance, RegistryRelation
from contracts.facets import TagSource


class Envelope(BaseModel):  # TODO(gen): canonical envelope fields from the Target Architecture
    title: str | None = None
    source_uri: str | None = None
    detected_category: str | None = None  # adapter routing key — never extension trust


class KnowledgeItem(BaseModel):
    """Envelope + body reference."""

    id: str
    content_hash: str
    envelope: Envelope
    body_ref: str
    lifecycle: str      # LFC-DRAFT ... LFC-ARCHIVED (TODO(gen): taxonomy enum)
    sensitivity: str    # SEN-* — write-gate enforced floor: max(sources)


class FacetAssignment(BaseModel):
    item_id: str
    facet: str          # TODO(gen): FacetScheme enum from the taxonomy
    value: str
    tag_source: TagSource
    confidence: float | None = None   # required when tag_source == auto
    decided_by: str | None = None     # required when tag_source == declared


class EdgeRecord(BaseModel):
    relation: RegistryRelation        # generated enum — Edge Registry SSOT
    src: str
    dst: str
    provenance: Provenance
    rationale: str | None = None      # required when provenance == inferred
    claim_scope: list[str] | None = None


class TrustEvent(BaseModel):
    """Append-only; the rating engine (Beta-Bernoulli) replays the log later (ADR-03)."""

    subject: str
    event: str
    weight_inputs: dict
    ts: datetime
