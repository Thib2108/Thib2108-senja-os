"""Repository ports — the swap seam (003 Principle 4, ADR-01 fallback lives here).

Satisfies Spec: 003 Block 6 snippet. Postgres+pgvector fallback would implement
these same Protocols beside surreal_impl.py; the p95<100ms tripwire decides.
"""

from typing import Protocol


class MessageStore(Protocol):
    async def append(self, conversation_id: str, text: str, lane: str, author: str): ...  # stamps id/turn/created_at server-side
    async def snapshot(self, conversation_id: str): ...  # immutable read for the harness


class ThreadIndexStore(Protocol):
    async def index(self, conversation_id: str): ...
    async def rebuild(self, conversation_id: str) -> None: ...  # projections are rebuildable (Principle 2)


class AtomStore(Protocol):
    async def upsert_patch(self, patch) -> None: ...  # incremental patches, opaque ULID ids (ADR-04)


class IntentLog(Protocol):
    async def enqueue(self, step: str, input_ref: str) -> None: ...
    async def claim(self, step: str, input_ref: str) -> bool: ...  # False if already done (idempotency)
    async def complete(self, step: str, input_ref: str) -> None: ...


class DecisionLog(Protocol):
    async def append(self, record) -> None: ...  # harness_kernel.decisions.DecisionRecord
