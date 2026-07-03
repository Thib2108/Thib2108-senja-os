# Sprint 01 — SurrealDB spike (the ADR-01 verdict)

> **Executor brief.** You are the executing engineer for this sprint, working in the
> `Thib2108/Thib2108-senja-os` repo on a local machine. The architect (Notion AI, working
> with Thibault) prepared this brief. Thibault is your channel back to the architect:
> when this document says **REPORT BACK**, print the requested output clearly so
> Thibault can copy-paste it.

## Standing rules (do not skip)

1. Read `AGENTS.md` at the repo root first. All of it applies.
2. **The contract tests define correct behavior. Never modify test bodies in
   `tests/contracts/` or `tests/test_gates.py` to make an implementation pass.**
   The only sanctioned test-side change in this sprint is the `conftest.py` fixture
   wiring described in Task 5.
3. All SurrealQL lives under `services/api/db/` (`.surql` files or a `queries.py`).
   `repos/surreal_impl.py` calls into `db/`, it never embeds query strings.
4. Do not invent relation names, table names, or fields. The schema is
   `services/api/db/migrations/*.surql`. If something seems missing, see **If blocked**.
5. Work on branch `sprint-01-surreal-spike`. Commit per task with `type: message`
   style (`feat:`, `test:`, `chore:`). Open a PR to `main` at the end — do not merge it.

## Context

- Spec: SDAI-CHAT-003 (backend). ADR-01 chose SurrealDB with an explicit fallback:
  if the spike can't hit **p95 < 100ms for conversation snapshot reads at 1,000
  messages**, we swap to Postgres+pgvector behind the same ports.
- The parity harness is already in place: `services/api/tests/contracts/` runs
  identical tests over `["memory", "surreal"]`. The in-memory reference
  (`repos/memory_impl.py`) defines correct behavior. The `surreal` param currently
  skips. **This sprint = implement the adapter, un-skip, pass the identical suite,
  then run the tripwire benchmark.**

## Task 0 — Environment

- Python 3.12+, [`uv`](https://docs.astral.sh/uv/) installed.
- From repo root: `uv sync` (workspace: `packages/harness_kernel`, `packages/contracts`, `services/api`).

## Task 1 — Baseline green

```bash
cd services/api && uv run pytest -v
```

Expected: all `[memory]` params pass, all `[surreal]` params skip, `test_gates.py`
passes. If anything unexpectedly fails at baseline, **stop** and REPORT BACK the
full output before changing anything.

## Task 2 — Local SurrealDB

Any one of:

```bash
# Docker
docker run --rm -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root memory
# or native (macOS)
brew install surrealdb/tap/surreal && surreal start --user root --pass root memory
# or install script
curl -sSf https://install.surrealdb.com | sh
```

Convention (used by fixtures and bench; in-memory server is fine for this sprint):

| Env var | Default |
|---|---|
| `SURREAL_URL` | `ws://127.0.0.1:8000/rpc` |
| `SURREAL_NS` | `senja` |
| `SURREAL_DB` | `dev` |
| `SURREAL_USER` / `SURREAL_PASS` | `root` / `root` |

## Task 3 — Migration runner

Implement `services/api/db/surreal.py`:

- `async def connect() -> client` — connect/signin/use from the env vars above.
  Check the installed `surrealdb` Python SDK version and use its actual API
  (`AsyncSurreal` in recent versions) — verify against the package, don't guess.
- `async def apply_migrations(client) -> list[str]` — execute
  `db/migrations/*.surql` in filename order, idempotently (a `migration` table
  recording applied filenames). Returns applied names.
- If a statement in `0002_knowledge.surql` fails on current SurrealDB syntax, fix
  the `.surql` file minimally, keep the schema semantics identical, and note the
  change in the PR description + REPORT BACK.

## Task 4 — `repos/surreal_impl.py`

Implement `SurrealMessageStore` and `SurrealIntentLog` satisfying the Protocols in
`repos/ports.py` (structural typing — no inheritance).

Hard requirements (these are exactly what the contract tests probe):

- **Turn allocation must be atomic in the database.** No read-count-then-write in
  Python — 50 concurrent appends must yield turns 1..50 with no gaps/dupes.
  Recommended: a per-conversation counter record updated atomically
  (`UPSERT ... SET n += 1 RETURN AFTER` inside a transaction), or a single
  transaction computing the count and creating the message.
- **Byte cap before write:** reject > 262,144 UTF-8 **bytes** with
  `models.MessageTooLarge` (the test uses a payload that is under the cap in chars
  but over in bytes).
- **No `update` or `delete` methods on the message store.** The test asserts the
  attributes don't exist.
- `snapshot()` returns `models.Snapshot` with messages ordered by `turn`, as
  detached copies.
- `IntentLog.claim(step, input_ref)` returns `True` **exactly once** per pending
  entry, atomically, under 10 concurrent claims; `False` after `complete()` and for
  never-enqueued keys.
- Server stamps `id` (ULID), `turn`, `created_at` — never accepted from the caller.

## Task 5 — Fixture wiring (sanctioned conftest change)

Update `services/api/tests/conftest.py`: for the `surreal` param —

- if `SURREAL_URL` is unset → `pytest.skip("SURREAL_URL not set")` (suite stays
  runnable without a DB);
- else connect, `apply_migrations`, yield the Surreal-backed store, and isolate
  tests (unique namespace/database per test, or wipe tables between tests).

Do not change any test bodies.

```bash
cd services/api && SURREAL_URL=ws://127.0.0.1:8000/rpc uv run pytest -v
```

Expected: **both** `[memory]` and `[surreal]` params pass every contract test.

## Task 6 — Tripwire benchmark

Create `services/api/scripts/bench_snapshot.py` (runnable via
`uv run python scripts/bench_snapshot.py`):

1. Fresh conversation; append 1,000 messages of realistic mixed size (~200–2,000
   chars) through `SurrealMessageStore.append`.
2. Warm up with 10 `snapshot()` calls, then measure 200 `snapshot()` calls with
   `time.perf_counter`.
3. Also measure append latency across the 1,000 seeding appends.
4. Print a table: p50 / p95 / p99 / max for snapshot and append, in ms, plus
   message count and SurrealDB mode (memory/rocksdb).

**Decision rule (ADR-01):** snapshot p95 < 100ms at 1,000 messages → SurrealDB
confirmed. Otherwise → REPORT BACK immediately; the architect decides on the
pgvector fallback. Do not start the fallback yourself.

## Task 7 — PR + REPORT BACK

Open PR `sprint-01-surreal-spike` → `main` (do not merge). Then print, clearly
delimited, for Thibault to copy back to the architect:

```
=== SPRINT 01 REPORT ===
1. PR URL + head commit SHA
2. Full `pytest -v` summary line(s) with SURREAL_URL set (counts: passed/skipped/failed)
3. Bench table (p50/p95/p99/max, snapshot + append) + SurrealDB mode + verdict vs 100ms
4. Any .surql changes made in Task 3 (file + before/after)
5. Any deviations from this brief, with one-line rationale each
6. Open questions for the architect
=== END REPORT ===
```

## If blocked

If a spec/schema ambiguity blocks you (missing field, contradictory constraint,
SDK limitation): don't improvise schema. Print a clearly delimited
`=== QUESTION FOR ARCHITECT ===` block explaining the blocker and 1–2 options with
trade-offs, and continue with whatever tasks aren't blocked. Thibault will relay it.
