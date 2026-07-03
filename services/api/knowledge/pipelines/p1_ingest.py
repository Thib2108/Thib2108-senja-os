"""P1 · Ingest & Normalize — SDAI-CHAT-004.

detect -> adapter -> envelope+body -> gauntlet (Genre · Topic · Sensitivity) -> register -> index

Invariants: idempotent by content hash (same hash = no-op); gauntlet blocks
registration without the minimum tag set (ADR-05); category detection never
trusts the file extension.
"""


async def run(source_ref: str, gauntlet_answers: dict) -> None:
    raise NotImplementedError  # TODO(004-slice)
