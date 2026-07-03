"""In-memory reference implementations — the parity baseline.

Transplanted pattern from the document-studio quarry (docs/HARVEST.md item 1):
the same contract tests run over ["memory", "surreal"]; these stores DEFINE
correct port behavior, and the real adapter must match it exactly. They are
also the rebuild-from-logs projection substrate (003 Principle 2).
"""

import asyncio
from datetime import datetime, timezone

from ulid import ULID

from models import MAX_MESSAGE_BYTES, Message, MessageTooLarge, Snapshot


class MemoryMessageStore:
    """Append-only by construction: no update method EXISTS (003 Principle 1)."""

    def __init__(self) -> None:
        self._by_conversation: dict[str, list[Message]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def append(
        self, conversation_id: str, text: str, lane: str, author: str
    ) -> Message:
        if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise MessageTooLarge(f"message exceeds {MAX_MESSAGE_BYTES} bytes")
        lock = self._locks.setdefault(conversation_id, asyncio.Lock())
        async with lock:  # turn allocation is atomic — monotonic, no gaps, no dupes
            messages = self._by_conversation.setdefault(conversation_id, [])
            message = Message(
                id=str(ULID()),
                conversation_id=conversation_id,
                author=author,
                lane=lane,
                text=text,
                turn=len(messages) + 1,
                created_at=datetime.now(timezone.utc),
            )
            messages.append(message)
            return message

    async def snapshot(self, conversation_id: str) -> Snapshot:
        # model_copy per message: mutating a snapshot can never touch the store
        return Snapshot(
            conversation_id=conversation_id,
            messages=[m.model_copy(deep=True) for m in self._by_conversation.get(conversation_id, [])],
        )


class MemoryIntentLog:
    """Transactional-outbox semantics (003 ADR-03): claim succeeds exactly once."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], str] = {}  # (step, input_ref) -> status
        self._lock = asyncio.Lock()

    async def enqueue(self, step: str, input_ref: str) -> None:
        async with self._lock:
            self._entries.setdefault((step, input_ref), "pending")

    async def claim(self, step: str, input_ref: str) -> bool:
        async with self._lock:
            if self._entries.get((step, input_ref)) == "pending":
                self._entries[(step, input_ref)] = "claimed"
                return True
            return False  # already claimed/done or never enqueued — replay skips

    async def complete(self, step: str, input_ref: str) -> None:
        async with self._lock:
            self._entries[(step, input_ref)] = "done"


class MemoryDecisionLog:
    """Append-only cognition log — record-once / replay-many."""

    def __init__(self) -> None:
        self._records: list[dict] = []

    async def append(self, record: dict) -> None:
        self._records.append(dict(record))

    def all(self) -> list[dict]:  # test/inspection surface, not part of the port
        return list(self._records)


class MemoryAtomStore:
    def __init__(self) -> None:
        self._atoms: dict[str, dict] = {}

    async def get(self, atom_id: str) -> dict | None:
        atom = self._atoms.get(atom_id)
        return dict(atom) if atom is not None else None

    async def upsert(self, atom: dict) -> None:
        self._atoms[atom["id"]] = dict(atom)
