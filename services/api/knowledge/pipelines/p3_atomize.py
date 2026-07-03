"""P3 · Atomization (map) — SDAI-CHAT-004.

per-section region proposal -> deterministic verbatim bind -> hard gate -> atoms
(claims, decisions, entities, tasks, unknowns)

Invariant: ungrounded atoms are dropped and logged, never persisted
(harness_kernel.gates.verify_verbatim is the gate — imported, not copied).
Crash mid-document => resume is idempotent via the intent log.
"""


async def run(item_id: str) -> None:
    raise NotImplementedError  # TODO(004-slice)
