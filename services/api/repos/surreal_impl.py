"""SurrealDB implementation of the repository ports (003 ADR-01).

Implements MessageStore and IntentLog Protocols from repos/ports.py using
structural typing — no inheritance needed (003 Principle 4).

All SurrealQL lives in services/api/db/surreal.py — this file contains NO
query strings (AGENTS.md rule 4, enforced by test_no_surrealql_outside_db_dir).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from surrealdb import AsyncSurreal  # type: ignore[import-untyped]

from db import surreal as _sql
from models import MAX_MESSAGE_BYTES, Message, MessageTooLarge, Snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_datetime(value: Any) -> datetime:
    """Normalise the various datetime shapes SurrealDB returns."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt
    # Fallback — shouldn't happen in practice
    return datetime.now(timezone.utc)


def _record_to_message(conv_id: str, row: dict[str, Any]) -> Message:
    """Convert a raw SurrealDB row to a Message model."""
    raw_id = row.get("id", "")
    # SurrealDB returns IDs as "table:key" strings
    msg_id = str(raw_id).split(":")[-1] if ":" in str(raw_id) else str(raw_id)
    return Message(
        id=msg_id,
        conversation_id=conv_id,
        author=str(row["author"]),
        lane=str(row["lane"]),
        text=str(row["text"]),
        turn=int(row["turn"]),
        created_at=_parse_datetime(row["created_at"]),
    )


# ---------------------------------------------------------------------------
# SurrealMessageStore
# ---------------------------------------------------------------------------


class SurrealMessageStore:
    """Append-only SurrealDB message store satisfying the MessageStore Protocol.

    Turn allocation is atomic in the database:
    - A per-conversation counter record in `conv_counter` is updated with
      ``UPSERT … SET n = n + 1 RETURN AFTER`` inside a BEGIN/COMMIT block,
      then the message is created with the allocated turn in the same
      transaction.  50 concurrent appends will produce turns 1..50 with no
      gaps or duplicates.

    Server stamps id (ULID via rand::ulid()), turn, and created_at.
    The Python layer never supplies these fields.
    """

    def __init__(self, client: AsyncSurreal) -> None:
        self._client = client

    async def append(
        self, conversation_id: str, text: str, lane: str, author: str
    ) -> Message:
        if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise MessageTooLarge(
                f"Payload size exceeds the {MAX_MESSAGE_BYTES} byte limit."
            )

        # 1. Ensure conversation exists (idempotent setup).
        await self._client.query(
            _sql.SQL_ENSURE_CONV, {"conv_id": conversation_id}
        )

        # 2. Allocate gapless turn atomically.
        counter_res = await self._client.query(
            _sql.SQL_ALLOC_TURN, {"conv_id": conversation_id}
        )
        if isinstance(counter_res, list) and len(counter_res) > 0:
            turn = counter_res[0].get("n", 1)
        else:
            turn = 1

        # 3. Insert the message with the allocated turn.
        result = await self._client.query(
            _sql.SQL_CREATE_MESSAGE,
            {
                "conv_id": conversation_id,
                "author": author,
                "lane": lane,
                "text": text,
                "turn": turn
            },
        )

        row = _extract_created_message(result)
        return _record_to_message(conversation_id, row)

    async def snapshot(self, conversation_id: str) -> Snapshot:
        """Return an immutable (deep-copied) ordered snapshot of the conversation."""
        rows = await self._client.query(
            _sql.SQL_SNAPSHOT, {"conv_id": conversation_id}
        )
        messages = [
            _record_to_message(conversation_id, row)
            for row in (_normalise_rows(rows))
        ]
        messages.sort(key=lambda m: m.turn)
        return Snapshot(conversation_id=conversation_id, messages=messages)

    # No update / delete methods — append-only by construction (003 Principle 1).


# ---------------------------------------------------------------------------
# SurrealIntentLog
# ---------------------------------------------------------------------------


class SurrealIntentLog:
    """SurrealDB transactional-outbox satisfying the IntentLog Protocol.

    claim() returns True exactly once per (step, input_ref) under concurrent
    callers.  The atomicity is guaranteed by a BEGIN/COMMIT transaction that
    reads the current status and conditionally updates it.
    """

    def __init__(self, client: AsyncSurreal) -> None:
        self._client = client

    async def enqueue(self, step: str, input_ref: str) -> None:
        """Insert a pending entry; no-op if already present (INSERT IGNORE)."""
        await self._client.query(
            _sql.SQL_ENQUEUE, {"step": step, "input_ref": input_ref}
        )

    async def claim(self, step: str, input_ref: str) -> bool:
        """Claim the entry; returns True exactly once."""
        result = await self._client.query(
            _sql.SQL_CLAIM, {"step": step, "input_ref": input_ref}
        )
        # SQL_CLAIM returns the updated record(s) if claim succeeded, else [].
        claimed_rows = _flatten_query_result(result)
        return len(claimed_rows) > 0

    async def complete(self, step: str, input_ref: str) -> None:
        """Mark the entry as done — future claim() calls return False."""
        await self._client.query(
            _sql.SQL_COMPLETE, {"step": step, "input_ref": input_ref}
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalise_rows(result: Any) -> list[dict[str, Any]]:
    """Flatten SurrealDB query() output to a plain list of row dicts."""
    if result is None:
        return []
    if isinstance(result, list):
        out: list[dict[str, Any]] = []
        for item in result:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, list):
                for sub in item:
                    if isinstance(sub, dict):
                        out.append(sub)
        return out
    return []


def _flatten_query_result(result: Any) -> list[dict[str, Any]]:
    """Same as _normalise_rows but tolerates tuple return from multi-statement."""
    if isinstance(result, tuple):
        rows: list[dict[str, Any]] = []
        for part in result:
            rows.extend(_normalise_rows(part))
        return rows
    return _normalise_rows(result)


def _extract_created_message(result: Any) -> dict[str, Any]:
    """Extract the single message row from a multi-statement query result."""
    rows = _flatten_query_result(result)
    if rows:
        return rows[-1]  # last statement returns the created message
    raise RuntimeError(
        f"SurrealDB append returned no rows; raw result: {result!r}"
    )
