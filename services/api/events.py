"""Atomic write+event, monotonic turns, SSE resume — SDAI-CHAT-003 Block 6."""


# Satisfies Spec: "write and event commit atomically"; "monotonic turn"
async def append_message(store, tx, intent_log, conversation_id: str, payload):
    async with tx():                                     # one transaction
        turn = await next_turn(conversation_id)          # allocated inside the tx — no client input
        msg = await store.append(conversation_id, payload.text, payload.lane, payload.author, turn=turn)
        await emit("message.appended", msg)              # same tx: no row without event
        await intent_log.enqueue("threading", msg.id)    # ADR-03: pipeline picks this up idempotently
    return msg


async def next_turn(conversation_id: str) -> int:  # TODO(003-slice): allocate inside tx
    raise NotImplementedError


async def emit(event: str, payload) -> None:  # TODO(003-slice): SSE fan-out + Last-Event-ID bookkeeping
    raise NotImplementedError
