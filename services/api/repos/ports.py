"""Repository ports — the swap seam (003 Principle 4, ADR-01 fallback lives here).

Satisfies Spec: 003 Block 6. Any class that structurally satisfies a Protocol is
a valid adapter — no inheritance needed. The parity contract tests in
tests/contracts/ run identically over every implementation; the in-memory
reference (repos/memory_impl.py) defines correct behavior, real adapters must
match it exactly. The Postgres+pgvector fallback would implement these same
Protocols beside surreal_impl.py; the p95<100ms tripwire decides.
"""

from typing import Protocol, runtime_checkable

from models import Message, Snapshot


@runtime_checkable
class MessageStore(Protocol):
    async def append(
        self, conversation_id: str, text: str, lane: str, author: str
    ) -> Message:
        """Append-only; stamps id/turn/created_at server-side. NO update method exists."""
        ...

    async def snapshot(self, conversation_id: str) -> Snapshot:
        """Immutable read for the harness."""
        ...


@runtime_checkable
class ThreadIndexStore(Protocol):
    async def index(self, conversation_id: str) -> list[dict]: ...

    async def rebuild(self, conversation_id: str) -> None:
        """Projections are rebuildable from the logs (003 Principle 2)."""
        ...


@runtime_checkable
class AtomStore(Protocol):
    async def get(self, atom_id: str) -> dict | None: ...
    async def upsert(self, atom: dict) -> None:
        """Incremental patches; opaque ULID ids (003 ADR-04)."""
        ...


@runtime_checkable
class IntentLog(Protocol):
    """The transactional outbox (003 ADR-03): write intent before acting."""

    async def enqueue(self, step: str, input_ref: str) -> None: ...

    async def claim(self, step: str, input_ref: str) -> bool:
        """True exactly once per (step, input_ref) — replay skips completed work."""
        ...

    async def complete(self, step: str, input_ref: str) -> None: ...


@runtime_checkable
class DecisionLog(Protocol):
    async def append(self, record: dict) -> None:
        """Append-only — record-once / replay-many cognition (harness_kernel.decisions)."""
        ...
