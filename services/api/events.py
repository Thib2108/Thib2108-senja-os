"""Event fan-out + append service — SDAI-CHAT-003 Block 6 (ADR-02: SSE).

Design note (atomicity, 003 Block 2): the message log IS the event source.
`message.appended` events are a projection of committed rows — SSE resume
(Last-Event-ID = turn) replays directly from the store, so a crash between
commit and fan-out loses nothing: the reconnecting client replays the gap.
In-process delivery is therefore best-effort; durability lives in the log.

Known gap (tracked for Sprint 03+): the threading intent enqueue happens
after the append transaction, not inside it — `test_append_fails_atomically`
stays open until the enqueue folds into SQL_APPEND_MESSAGE or a log sweeper
reconciles missed entries. Replay safety already holds (enqueue is
idempotent by construction: deterministic intent id per (step, input_ref)).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from models import Message


class EventBroker:
    """In-process pub/sub per conversation. Publishing never blocks appends
    (put_nowait on unbounded queues; SSE generators drain promptly)."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[Message]]] = defaultdict(set)

    def subscribe(self, conversation_id: str) -> asyncio.Queue[Message]:
        queue: asyncio.Queue[Message] = asyncio.Queue()
        self._subscribers[conversation_id].add(queue)
        return queue

    def unsubscribe(self, conversation_id: str, queue: asyncio.Queue[Message]) -> None:
        self._subscribers[conversation_id].discard(queue)
        if not self._subscribers[conversation_id]:
            del self._subscribers[conversation_id]

    async def publish(self, conversation_id: str, message: Message) -> None:
        for queue in tuple(self._subscribers.get(conversation_id, ())):
            queue.put_nowait(message)


# Satisfies Spec: monotonic turn (allocated inside the store's append
# transaction — Sprint 01); event = projection of the committed row.
async def append_message(
    store, intent_log, broker: EventBroker,
    conversation_id: str, text: str, lane: str, author: str,
) -> Message:
    msg = await store.append(conversation_id, text, lane, author)
    await intent_log.enqueue("threading", msg.id)  # ADR-03 outbox (idempotent)
    await broker.publish(conversation_id, msg)     # best-effort; resume covers gaps
    return msg
