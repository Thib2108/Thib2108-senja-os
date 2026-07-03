"""API slice tests — SDAI-CHAT-003 Block 2 criteria enforced at the HTTP edge.

Runs over every store implementation via the parity `message_store` fixture
(memory always; surreal when SURREAL_URL is set) — the API behaves
identically regardless of the adapter behind the port.
"""

import asyncio
import json

import httpx
import pytest

from app import create_app
from models import MAX_MESSAGE_BYTES
from repos.memory_impl import MemoryIntentLog


@pytest.fixture
async def client(message_store):
    application = create_app(store=message_store, intent_log=MemoryIntentLog())
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _read_events(response, count):
    """Parse SSE lines into events; returns once `count` data events seen."""
    events, current = [], {}
    async for line in response.aiter_lines():
        line = line.strip()
        if not line:
            if "data" in current:
                events.append(current)
                if len(events) == count:
                    return events
            current = {}
        elif ":" in line:
            key, _, value = line.partition(":")
            current[key.strip()] = value.strip()
    return events


async def test_post_message_round_trip(client):
    r = await client.post("/v1/conversations/conv-1/messages", json={"text": "hello"})
    assert r.status_code == 201
    body = r.json()
    assert body["turn"] == 1 and body["text"] == "hello"
    assert body["id"] and body["created_at"]  # server-stamped

    r2 = await client.post("/v1/conversations/conv-1/messages", json={"text": "again"})
    assert r2.json()["turn"] == 2

    snap = (await client.get("/v1/conversations/conv-1/snapshot")).json()
    assert [m["turn"] for m in snap["messages"]] == [1, 2]


async def test_server_stamped_fields_reject_client_values(client):
    """003 Principle 3 / Block 7 #3: named test."""
    forged = (
        ("turn", 99),
        ("id", "h4x"),
        ("created_at", "2020-01-01T00:00:00Z"),
        ("createdAt", "2020-01-01T00:00:00Z"),
        ("provenance", {"forged": True}),
    )
    for field, value in forged:
        r = await client.post(
            "/v1/conversations/conv-1/messages", json={"text": "x", field: value}
        )
        assert r.status_code == 422, field
        assert r.json()["error"] == "server_stamped_field", field
    # and nothing was written
    snap = (await client.get("/v1/conversations/conv-1/snapshot")).json()
    assert snap["messages"] == []


async def test_size_cap_returns_413_never_truncates(client):
    """003 Block 2: >256KB -> 413 typed error. Byte cap, not chars — multibyte
    payload stays under the char count but over the byte cap."""
    over = "a" * (MAX_MESSAGE_BYTES - 1) + "é"  # MAX chars, MAX+1 bytes
    r = await client.post("/v1/conversations/conv-1/messages", json={"text": over})
    assert r.status_code == 413
    assert r.json()["error"] == "message_too_large"

    at_cap = "a" * MAX_MESSAGE_BYTES
    r2 = await client.post("/v1/conversations/conv-1/messages", json={"text": at_cap})
    assert r2.status_code == 201  # exactly at cap is legal — no silent truncation either way


async def test_sse_resume_replays_without_dupes_or_gaps(client):
    """003 Block 2: Last-Event-ID resume — no duplicates, no gaps."""
    for i in range(3):
        await client.post("/v1/conversations/conv-1/messages", json={"text": f"msg {i}"})

    async with client.stream(
        "GET", "/v1/conversations/conv-1/events", headers={"Last-Event-ID": "1"}
    ) as r:
        events = await asyncio.wait_for(_read_events(r, 2), timeout=10)

    assert [e["id"] for e in events] == ["2", "3"]
    assert [json.loads(e["data"])["turn"] for e in events] == [2, 3]


async def test_sse_live_fanout(client):
    """A message posted while a stream is open arrives as a live event."""
    async with client.stream("GET", "/v1/conversations/conv-live/events") as r:
        post = asyncio.create_task(
            client.post("/v1/conversations/conv-live/messages", json={"text": "live"})
        )
        events = await asyncio.wait_for(_read_events(r, 1), timeout=10)
        await post
    assert json.loads(events[0]["data"])["text"] == "live"
    assert events[0]["event"] == "message.appended"


async def test_bearer_token_enforced_when_configured(client, monkeypatch):
    monkeypatch.setenv("SENJA_API_TOKEN", "sekrit")
    r = await client.post("/v1/conversations/conv-1/messages", json={"text": "x"})
    assert r.status_code == 401
    r = await client.post(
        "/v1/conversations/conv-1/messages",
        json={"text": "x"},
        headers={"Authorization": "Bearer sekrit"},
    )
    assert r.status_code == 201
    assert (await client.get("/healthz")).status_code == 200  # healthz exempt
