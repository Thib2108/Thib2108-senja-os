"""P4 · Topology (reduce) — SDAI-CHAT-004.

entity resolution (12B fork-critical) -> registry-edge proposal -> independence
walk -> graph.patch

Invariants: every edge uses a RegistryRelation with a valid provenance class;
`corroborates` raises confidence only after the lineage-independence walk
(echoes discount); `contradicts` opens a resolution item, never moves trust.
"""


async def run(item_id: str) -> None:
    raise NotImplementedError  # TODO(004-slice)
