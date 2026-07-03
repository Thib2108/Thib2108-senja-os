"""FastAPI wiring, SSE fan-out, auth middleware — SDAI-CHAT-003 Block 6.

STRIDE controls at this layer: bind 127.0.0.1 (see run command below),
per-install bearer token on every route when SENJA_API_TOKEN is set, and
payload rejection for server-stamped fields (003 Principle 3).

Local run:
    cd services/api
    SURREAL_URL=ws://127.0.0.1:8000/rpc uv run uvicorn app:app --host 127.0.0.1 --port 8080
    # interactive docs: http://127.0.0.1:8080/docs
    # without SURREAL_URL the API runs on the in-memory store (data lost on restart)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from events import EventBroker, append_message
from models import Message, MessageTooLarge, Snapshot

_ALLOWED_FIELDS = {"text", "lane", "author"}
_SERVER_STAMPED_FIELDS = {"id", "turn", "created_at", "createdAt", "provenance"}
_LANES = {"message", "cot", "todo", "tool"}
_AUTHORS = {"user", "assistant"}


def create_app(store=None, intent_log=None, broker: EventBroker | None = None) -> FastAPI:
    """App factory. Pass adapters directly (tests), or leave None to build
    from env at startup: SURREAL_URL set -> SurrealDB adapters, else memory."""

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        client = None
        if application.state.store is None:
            if os.environ.get("SURREAL_URL"):
                from db.surreal import apply_migrations, connect
                from repos.surreal_impl import SurrealIntentLog, SurrealMessageStore

                client = await connect()
                await apply_migrations(client)
                application.state.store = SurrealMessageStore(client)
                application.state.intent_log = SurrealIntentLog(client)
            else:
                from repos.memory_impl import MemoryIntentLog, MemoryMessageStore

                application.state.store = MemoryMessageStore()
                application.state.intent_log = MemoryIntentLog()
        yield
        if client is not None:
            await client.close()

    application = FastAPI(title="senja-os api", lifespan=lifespan)
    application.state.store = store
    application.state.intent_log = intent_log
    application.state.broker = broker or EventBroker()

    @application.middleware("http")
    async def bearer_auth(request: Request, call_next):
        # S(poofing) control: per-install token, enforced whenever configured.
        token = os.environ.get("SENJA_API_TOKEN")
        if token and request.url.path != "/healthz":
            if request.headers.get("authorization") != f"Bearer {token}":
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

    @application.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # response_model on the decorator (not a return annotation): the error
    # paths return JSONResponse instances, which legally bypass the model —
    # a `Message | JSONResponse` annotation is not a valid response field.
    @application.post(
        "/v1/conversations/{conversation_id}/messages",
        status_code=201,
        response_model=Message,
    )
    async def post_message(conversation_id: str, payload: dict[str, Any], request: Request):
        # 003 Principle 3: server-stamped fields are never accepted from clients.
        stamped = _SERVER_STAMPED_FIELDS & payload.keys()
        if stamped:
            return JSONResponse(
                {"error": "server_stamped_field", "fields": sorted(stamped)},
                status_code=422,
            )
        unknown = payload.keys() - _ALLOWED_FIELDS
        if unknown:
            return JSONResponse(
                {"error": "unknown_field", "fields": sorted(unknown)}, status_code=422
            )
        text = payload.get("text")
        if not isinstance(text, str) or not text:
            return JSONResponse({"error": "invalid_text"}, status_code=422)
        lane = payload.get("lane", "message")
        if lane not in _LANES:
            return JSONResponse({"error": "invalid_lane"}, status_code=422)
        author = payload.get("author", "user")
        if author not in _AUTHORS:
            return JSONResponse({"error": "invalid_author"}, status_code=422)

        try:
            return await append_message(
                request.app.state.store,
                request.app.state.intent_log,
                request.app.state.broker,
                conversation_id,
                text,
                lane,
                author,
            )
        except MessageTooLarge:
            # 003 Block 2: reject with a typed error — never truncate silently.
            return JSONResponse({"error": "message_too_large"}, status_code=413)

    @application.get("/v1/conversations/{conversation_id}/snapshot")
    async def get_snapshot(conversation_id: str, request: Request) -> Snapshot:
        """Immutable read for the harness (003 Block 6 MessageStore.snapshot)."""
        return await request.app.state.store.snapshot(conversation_id)

    @application.get("/v1/conversations/{conversation_id}/events")
    async def get_events(
        conversation_id: str, request: Request, until_turn: int | None = None
    ):
        """SSE stream (ADR-02), resumable via Last-Event-ID = last seen turn.
        Replays the gap from the store, then goes live — no duplicates, no
        gaps, guaranteed by monotonic turns.

        `until_turn` (optional): bounded catch-up read — the server closes
        the stream once the given turn has been sent. Also what keeps the
        stream deterministic under buffering test transports."""
        store = request.app.state.store
        broker: EventBroker = request.app.state.broker
        raw = request.headers.get("last-event-id")
        try:
            last_turn = int(raw) if raw else 0
        except ValueError:
            last_turn = 0

        async def event_stream():
            # Subscribe BEFORE the replay snapshot so nothing published during
            # replay is missed; monotonic turns make the dedup exact.
            queue = broker.subscribe(conversation_id)
            try:
                sent = last_turn
                snap = await store.snapshot(conversation_id)
                for m in snap.messages:
                    if m.turn > sent:
                        yield {
                            "event": "message.appended",
                            "id": str(m.turn),
                            "data": m.model_dump_json(),
                        }
                        sent = m.turn
                        if until_turn is not None and sent >= until_turn:
                            return
                if until_turn is not None and sent >= until_turn:
                    return
                while True:
                    m = await queue.get()
                    if m.turn > sent:
                        yield {
                            "event": "message.appended",
                            "id": str(m.turn),
                            "data": m.model_dump_json(),
                        }
                        sent = m.turn
                        if until_turn is not None and sent >= until_turn:
                            return
            finally:
                broker.unsubscribe(conversation_id, queue)

        return EventSourceResponse(event_stream())

    return application


app = create_app()
