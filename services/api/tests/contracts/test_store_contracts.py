"""Parity contract tests — the memory reference defines correct behavior;
every real adapter must pass this identical suite (003 ADR-01 mechanism).

Named tests trace to SDAI-CHAT-003 Block 7.
"""

import asyncio

import pytest

from models import MAX_MESSAGE_BYTES, MessageTooLarge


async def test_message_round_trip(message_store):
    msg = await message_store.append("conv-1", "hello world", "message", "user")
    assert msg.turn == 1
    assert msg.id and msg.created_at  # server-stamped

    snap = await message_store.snapshot("conv-1")
    assert len(snap.messages) == 1
    assert snap.messages[0].text == "hello world"


async def test_turns_monotonic_under_concurrency(message_store):
    """003 Block 7 #6: N parallel writers — no gaps, no duplicates."""
    n = 50
    results = await asyncio.gather(
        *[message_store.append("conv-1", f"msg {i}", "message", "user") for i in range(n)]
    )
    turns = sorted(m.turn for m in results)
    assert turns == list(range(1, n + 1))


async def test_no_update_path_on_messages(message_store):
    """003 Block 7 #8 — the delete test: an 'edit message' convenience would
    silently destroy the grounding substrate."""
    assert not hasattr(message_store, "update")
    assert not hasattr(message_store, "delete")


async def test_snapshot_is_immutable_read(message_store):
    await message_store.append("conv-1", "original", "message", "user")
    snap = await message_store.snapshot("conv-1")
    snap.messages[0].text = "tampered"

    fresh = await message_store.snapshot("conv-1")
    assert fresh.messages[0].text == "original"


async def test_size_cap_counts_bytes_not_chars(message_store):
    """003 Block 7 #1: multibyte payload under the char count but over the byte cap."""
    at_cap = "a" * MAX_MESSAGE_BYTES
    msg = await message_store.append("conv-1", at_cap, "message", "user")
    assert msg.turn == 1  # exactly at cap is accepted

    over_in_bytes_only = "a" * (MAX_MESSAGE_BYTES - 1) + "\u00e9"  # chars == cap, bytes == cap+1
    with pytest.raises(MessageTooLarge):
        await message_store.append("conv-1", over_in_bytes_only, "message", "user")


async def test_intent_log_claim_exactly_once(intent_log):
    """003 Block 7 #2: crash-replay runs each step exactly once."""
    await intent_log.enqueue("threading", "msg-1")
    outcomes = await asyncio.gather(*[intent_log.claim("threading", "msg-1") for _ in range(10)])
    assert sum(outcomes) == 1


async def test_intent_log_replay_skips_completed(intent_log):
    await intent_log.enqueue("threading", "msg-1")
    assert await intent_log.claim("threading", "msg-1") is True
    await intent_log.complete("threading", "msg-1")

    assert await intent_log.claim("threading", "msg-1") is False  # replay after crash: no rerun


async def test_intent_log_claim_unknown_entry_is_false(intent_log):
    assert await intent_log.claim("threading", "never-enqueued") is False
