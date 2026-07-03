"""Edge vocabulary — GENERATED from the Edge Registry (Notion), v0.2.

DO NOT HAND-EDIT relation names. New edge ⇒ registry change first, regenerate second.
Storage names are lower_snake (the enum *values*); the model-facing surface is
UPPER_SNAKE (the enum *member names*). Write gates lowercase model output to canonical.

Registry SSOT: "Edge Registry — Canonical Edge Vocabulary (Graph Spine)" (Notion).
Budget: ≤ 25 canonical edges. `entails` is NOT an edge — it is the `entail_score`
property on grounded_by (registry v0.2 decision).
"""

from enum import StrEnum

EDGE_REGISTRY_VERSION = "0.2"


class RegistryRelation(StrEnum):
    # Family 1 · Provenance & lineage
    DERIVED_FROM = "derived_from"
    ATTRIBUTED_TO = "attributed_to"
    AUTHORED_BY = "authored_by"
    PUBLISHED_BY = "published_by"
    TRANSLATION_OF = "translation_of"
    SUPERSEDED_BY = "superseded_by"
    INSTANTIATES = "instantiates"
    # Family 2 · Epistemic (claim-scoped)
    GROUNDED_BY = "grounded_by"      # carries entail_score property
    CORROBORATES = "corroborates"    # confidence moves only after the independence walk
    CONTRADICTS = "contradicts"      # opens a resolution loop; never moves trust directly
    # Family 3 · Structural / functional (directional, item-level)
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    ENABLES = "enables"
    BLOCKS = "blocks"
    MEASURED_BY = "measured_by"
    INFORMS = "informs"
    # Family 4 · Discourse (thread/atom level; symmetric)
    CONVERGES = "converges"
    INTERSECTS = "intersects"
    # Family 5 · Ownership & routing
    OWNED_BY = "owned_by"
    ABOUT_BRANCH = "about_branch"
    ABOUT_SUBJECT = "about_subject"
    LIKELY_RECIPIENT = "likely_recipient"
    PRODUCES = "produces"


class Provenance(StrEnum):
    """Who/what asserted an edge. `inferred` requires a rationale (gate-enforced)."""

    ASSERTED = "asserted"
    INFERRED = "inferred"
    RECORDED = "recorded"
    DECLARED = "declared"
    DERIVED = "derived"


# Alias map (dialect → canonical). Direction flips are handled at the gate:
#   supersedes(A, B) ≡ superseded_by(B, A)
# TODO(gen): emit the full alias table from the registry page.
ALIASES: dict[str, tuple[RegistryRelation, bool]] = {
    # alias: (canonical, flip_direction)
    "supersedes": (RegistryRelation.SUPERSEDED_BY, True),
}
