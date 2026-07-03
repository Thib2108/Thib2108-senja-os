"""Write-time gates — the backend half of the grounding contract (003 Block 6).

Mirrors the harness gate: defense in depth, but the *implementation* is imported
from the shared kernel — never re-implemented here (004 ADR-04).
"""

from harness_kernel.gates import verify_verbatim

__all__ = ["verify_verbatim", "check_inferred_edge", "check_view_block_refs"]


def check_inferred_edge(provenance: str, rationale: str | None, endpoint_highlights: int) -> bool:
    """relates edges with provenance='inferred' require rationale + >= 2 endpoint highlights."""
    if provenance != "inferred":
        return True
    return bool(rationale) and endpoint_highlights >= 2


def check_view_block_refs(atom_ids: set[str], referenced: list[str]) -> bool:
    """view_block.elements[*].atomId must resolve — dangling refs are rejected."""
    return all(ref in atom_ids for ref in referenced)
