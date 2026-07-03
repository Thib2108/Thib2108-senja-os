"""SurrealDB implementation of the repository ports (003 ADR-01).

Structurally satisfies MessageStore and IntentLog from repos/ports.py.
All SurrealQL lives in services/api/db/surreal.py — no query strings here
(AGENTS.md rule 4). The parity contract tests in tests/contracts/ must pass
identically against this adapter and the in-memory reference.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any

from surrealdb import AsyncSurreal  # type: ignore[import-untyped]

from db import surreal as _sql
from models import MAX_MESSAGE_BYTES, Message, MessageTooLarge, Snapshot

_TXN_RETRIES = 50
_TXN_BACKOFF_S = 0.004  # linear: 4ms, 8ms, ... — counter contention clears fast

_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32


def _new_ulid() -> str:
    """Dependency-free ULID (ADR-04): 48-bit ms timestamp + 80 bits randomness,
    26 chars Crockford base32 — lexicographically sortable by creation time."""
    value = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
    return "".join(
        _ULID_ALPHABET[(value >> (5 * shift)) & 31] for shift in range(25, -1, -1)
    )


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


def _is_txn_conflict(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "retr" in msg or "conflict" in msg  # 'retried'/'retry'/'conflict'


# ---------------------------------------------------------------------------
# SurrealMessageStore
# ---------------------------------------------------------------------------


class SurrealMessageStore:
    """Append-only message store. Turn allocation and message creation happen
    in ONE database transaction (SQL_APPEND_MESSAGE) — monotonic, gapless,
    duplicate-free under concurrency, and crash-safe (a crash can never leave
    an allocated turn without its message).

    SDK reality (verified in CI): transaction batches always return None,
    and a conflicted transaction aborts WITHOUT raising. The adapter
    therefore generates the ULID id itself (ruling #5), commits the
    write-only transaction, and reads the message back by known id — the
    read-back doubles as the success check. Absent message = conflict
    abort = retry the whole transaction.

    Safety: an aborted transaction creates nothing and rolls back the
    counter (no turn gaps); a duplicate commit would fail loudly on the
    existing ULID rather than double-append.

    turn (counter) and created_at (schema VALUE) are server-stamped.
    No update or delete methods exist — append-only by construction (Principle 1).
    """

    def __init__(self, client: AsyncSurreal) -> None:
        self._client = client

    async def append(
        self, conversation_id: str, text: str, lane: str, author: str
    ) -> Message:
        if len(text.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise MessageTooLarge(f"message exceeds {MAX_MESSAGE_BYTES} bytes")

        msg_id = _new_ulid()
        params = {
            "conv_id": conversation_id,
            "msg_id": msg_id,
            "author": author,
            "lane": lane,
            "text": text,
        }
        for attempt in range(_TXN_RETRIES):
            try:
                await self._client.query(_sql.SQL_APPEND_MESSAGE, params)
            except Exception as exc:  # loud conflict — retry; anything else raises
                if _is_txn_conflict(exc):
                    await asyncio.sleep(_TXN_BACKOFF_S * (attempt + 1))
                    continue
                raise

            # Read-back by known id is the success check: conflicted
            # transactions abort silently (SDK returns None either way).
            rows = _normalise_rows(
                await self._client.query(_sql.SQL_GET_MESSAGE, {"msg_id": msg_id})
            )
            if rows:
                return _record_to_message(conversation_id, rows[0])
            await asyncio.sleep(_TXN_BACKOFF_S * (attempt + 1))

        raise RuntimeError(
            f"append transaction still conflicting after {_TXN_RETRIES} retries"
        )

    async def snapshot(self, conversation_id: str) -> Snapshot:
        rows = await self._client.query(_sql.SQL_SNAPSHOT, {"conv_id": conversation_id})
        messages = [_record_to_message(conversation_id, r) for r in _normalise_rows(rows)]
        messages.sort(key=lambda m: m.turn)  # belt-and-braces over ORDER BY
        return Snapshot(conversation_id=conversation_id, messages=messages)

    # No update / delete methods — append-only by construction (003 Principle 1).


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
