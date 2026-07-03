# Sprint 02 — API slice: append → event → serve

**Goal:** wire FastAPI to the Sprint-01-proven adapters so the 003 vertical
slice runs end-to-end over HTTP: turn appended → persisted atomically →
served to UI and harness (snapshot + SSE).

**Branch:** `sprint-02-api-slice` · **Spec:** SDAI-CHAT-003 @ 0.1.2

## Scope

| In | Out (later sprints) |
|---|---|
| `POST /v1/conversations/{id}/messages` (201 / 413 / 422) | Thread index pipeline + `GET /v1/threads/{id}/index` |
| `GET /v1/conversations/{id}/snapshot` (harness read) | `gatesvc.py` wiring (highlights/atoms — needs atom writes) |
| `GET /v1/conversations/{id}/events` — SSE, `Last-Event-ID` resume | Studio endpoints (`/v1/studio/generate`, comments) |
| Bearer-token middleware (`SENJA_API_TOKEN`) | UI shell (SDAI-CHAT-002) |
| Named tests: `test_server_stamped_fields_reject_client_values`, `test_no_surrealql_outside_db_dir` | `test_append_fails_atomically` (see known gap) |

## Design decisions

1. **The message log IS the event source.** SSE event id = turn number;
   resume replays the gap straight from the store, then goes live via the
   in-process broker. No duplicates and no gaps follow from turn
   monotonicity (proven in Sprint 01), not from broker bookkeeping.
2. **API tests run over both stores** via the parity `message_store`
   fixture — the HTTP edge cannot behave differently on memory vs surreal.
3. **Known gap (tracked):** the threading intent enqueue happens after the
   append transaction, not inside it. `test_append_fails_atomically` stays
   open until enqueue folds into `SQL_APPEND_MESSAGE` or a sweeper
   reconciles. Enqueue is already idempotent, so replay safety holds.

## Local run (first clickable localhost)

```bash
# terminal 1 — SurrealDB (or skip: memory store, data lost on restart)
surreal start --user root --pass root rocksdb:senja.db

# terminal 2
cd services/api
SURREAL_URL=ws://127.0.0.1:8000/rpc uv run uvicorn app:app --host 127.0.0.1 --port 8080
```

Then open **http://127.0.0.1:8080/docs** — post messages, read snapshots,
and watch `curl -N -H 'Last-Event-ID: 0' http://127.0.0.1:8080/v1/conversations/demo/events` stream.

## Verdict process

Same as Sprint 01: CI runs the full suite on PR; architect reads check
runs; user pastes logs when red. Do not merge until CI is green and the
spec sync (if any behavior diverged) has landed.
