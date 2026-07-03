"""P2 · Facet Classification — SDAI-CHAT-004. Re-runnable anytime.

deterministic facets (Format, Language) -> SLM facets (Genre, Function, Register,
Topic->branch+subject) as `auto`+confidence -> promotion queue

Invariant: a re-run produces ZERO modifications to declared or locked assignments
(test_rerun_zero_clobbers_on_declared_facets).
"""


async def run(item_id: str) -> None:
    raise NotImplementedError  # TODO(004-slice)
