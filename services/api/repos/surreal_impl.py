"""SurrealDB implementation of the repository ports (003 ADR-01).

Structurally satisfies MessageStore and IntentLog from repos/ports.py.
All SurrealQL lives in services/api/db/surreal.py — no query strings here
(AGENTS.md rule 4). The parity contract tests in tests/contracts/ must pass
identically against this adapter and the in-memory reference.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from surrealdb import AsyncSurreal  # type: ignore[import-untyped]

from db import surreal as _sql
from models import MAX_MESSAGE_BYTES, Message, MessageTooLarge, Snapshot


# ---------------------------------------------------------------------------
# Result-shape helpers (SDK returns vary by statement kind and version)
# ---------------------------------------------------------------------------


def _normalise_rows(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    if isinstance(result, dict):
        return [result]
    if isinstance(result, (list, tuple)):
        out: list[dict[str, Any]] = []
        for item in result:
            out.extend(_normalise_rows(item))
        return out
    return []


def _record_key(raw_id: Any) -> str:
    """'message:⟨01H…⟩' / RecordID -> bare key string."""
    s = str(raw_id)
    if ":" in s:
        s = s.split(":", 1)[1]
    return s.strip("⟨⟩`")


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"unexpected created_at shape: {value!r}")


def _record_to_message(conv_id: str, row: dict[str, Any]) -> Message:
    return Message(
        id=_record_key(row["id"]),
        conversation_id=conv_id,
        author=str(row["author"]),
        lane=str(row["lane"]),
        text=str(row["text"]),
        turn=int(row["turn"]),
        created_at=_parse_datetime(row["created_at"]),
    )


def _extract_created_message(result: Any) -> dict[str, Any]:
    """The append transaction returns several statement results; the created
    message is the last row that has a `turn` field."""
    for row in reversed(_normalise_rows(result)):
        if "turn" in row and "text" in row:
            return row
    raise RuntimeError(f"append returned no message row; raw result: {result!r}")


# ---------------------------------------------------------------------------
# SurrealMessageStore
# ---------------------------------------------------------------------------


class SurrealMessageStore:
    """Append-only message store. Turn allocation and message creation happen
    in ONE database transaction (SQL_APPEND_MESSAGE) — monotonic, gapless,
    duplicate-free under concurrency, and crash-safe (a crash can never leave
    an allocated turn without its message).

    Server stamps id (rand::ulid()), turn (counter), created_at (schema VALUE).
    No update or delete methods exist — append-only by construction (Principle 1).
    """

    def __init__(self, client: AsyncSurreal) -> None:
        self._client = client

    async def append(
        self, conversation_id: str, text: str, lane: str, author: str
    ) -> Message:
        if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise MessageTooLarge(f"message exceeds {MAX_MESSAGE_BYTES} bytes")

        result = await self._client.query(
            _sql.SQL_APPEND_MESSAGE,
            {
                "conv_id": conversation_id,
                "author": author,
                "lane": lane,
                "text": text,
            },
        )
        return _record_to_message(conversation_id, _extract_created_message(result))

    async def snapshot(self, conversation_id: str) -> Snapshot:
        rows = await self._client.query(_sql.SQL_SNAPSHOT, {"conv_id": conversation_id})
        messages = [_record_to_message(conversation_id, r) for r in _normalise_rows(rows)]
        messages.sort(key=lambda m: m.turn)  # belt-and-braces over ORDER BY
        return Snapshot(conversation_id=conversation_id, messages=messages)


# ---------------------------------------------------------------------------
# SurrealIntentLog
# ---------------------------------------------------------------------------


class SurrealIntentLog:
    """Transactional outbox (003 ADR-03). Deterministic record id per
    (step, input_ref); claim is a single conditional UPDATE, so exactly one
    concurrent caller sees a non-empty RETURN AFTER."""

    def __init__(self, client: AsyncSurreal) -> None:
        self._client = client

    async def enqueue(self, step: str, input_ref: str) -> None:
        await self._client.query(_sql.SQL_ENQUEUE, {"step": step, "input_ref": input_ref})

    async def claim(self, step: str, input_ref: str) -> bool:
        result = await self._client.query(_sql.SQL_CLAIM, {"step": step, "input_ref": input_ref})
        return len(_normalise_rows(result)) > 0

    async def complete(self, step: str, input_ref: str) -> None:
        await self._client.query(_sql.SQL_COMPLETE, {"step": step, "input_ref": input_ref})
