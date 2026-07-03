"""ADR-01 tripwire benchmark (Sprint-01 Task 6).

Seeds 1,000 messages of realistic mixed size into one conversation through
SurrealMessageStore.append, then measures 200 snapshot() reads.

Decision rule: snapshot p95 < 100ms at 1,000 messages -> SurrealDB confirmed.
Otherwise report to the architect; the pgvector fallback is their call.

Run from services/api:  uv run python scripts/bench_snapshot.py
(Requires a running SurrealDB; honours SURREAL_* env vars.)
"""

import asyncio
import os
import pathlib
import random
import sys
import time
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from db.surreal import apply_migrations, connect  # noqa: E402
from repos.surreal_impl import SurrealMessageStore  # noqa: E402

N_MESSAGES = 1_000
N_WARMUP = 10
N_SNAPSHOTS = 200
TRIPWIRE_MS = 100.0


def pct(samples: list[float], p: float) -> float:
    xs = sorted(samples)
    k = min(len(xs) - 1, max(0, round(p / 100 * (len(xs) - 1))))
    return xs[k]


def row(name: str, xs: list[float]) -> str:
    return (
        f"{name:<10} p50={pct(xs, 50):8.2f}  p95={pct(xs, 95):8.2f}  "
        f"p99={pct(xs, 99):8.2f}  max={max(xs):8.2f}  (ms, n={len(xs)})"
    )


async def main() -> int:
    client = await connect()
    ns = os.environ.get("SURREAL_NS", "senja")
    await client.use(ns, f"bench_{uuid.uuid4().hex[:8]}")
    await apply_migrations(client)
    store = SurrealMessageStore(client)

    conv = "bench-conv"
    rng = random.Random(42)

    append_ms: list[float] = []
    for i in range(N_MESSAGES):
        text = "lorem ipsum " * rng.randint(17, 170)  # ~200–2000 chars
        t0 = time.perf_counter()
        await store.append(conv, text, "message", "user" if i % 2 else "assistant")
        append_ms.append((time.perf_counter() - t0) * 1000)

    for _ in range(N_WARMUP):
        await store.snapshot(conv)

    snap_ms: list[float] = []
    snap = None
    for _ in range(N_SNAPSHOTS):
        t0 = time.perf_counter()
        snap = await store.snapshot(conv)
        snap_ms.append((time.perf_counter() - t0) * 1000)

    assert snap is not None and len(snap.messages) == N_MESSAGES, (
        f"expected {N_MESSAGES} messages, got {len(snap.messages) if snap else 0}"
    )

    p95 = pct(snap_ms, 95)
    verdict = "PASS — SurrealDB confirmed (ADR-01)" if p95 < TRIPWIRE_MS else (
        "FAIL — tripwire exceeded; report to architect (pgvector fallback decision)"
    )

    print("=== ADR-01 TRIPWIRE BENCH ===")
    print(f"messages={N_MESSAGES}  snapshots={N_SNAPSHOTS}  url={os.environ.get('SURREAL_URL', 'default')}")
    print(row("snapshot", snap_ms))
    print(row("append", append_ms))
    print(f"tripwire: snapshot p95 {p95:.2f}ms vs {TRIPWIRE_MS:.0f}ms -> {verdict}")
    print("=== END BENCH ===")

    await client.close()
    return 0 if p95 < TRIPWIRE_MS else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
