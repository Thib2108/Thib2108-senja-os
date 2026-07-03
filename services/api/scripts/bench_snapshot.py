import asyncio
import os
import random
import string
import sys
import time
import uuid
from typing import Callable

from db.surreal import apply_migrations, connect
from repos.surreal_impl import SurrealMessageStore


def _generate_text(length: int) -> str:
    """Generate a random string of printable ASCII characters."""
    return "".join(random.choices(string.ascii_letters + string.digits + " ", k=length))


def _percentile(data: list[float], p: float) -> float:
    """Calculate the p-th percentile of a list of floats."""
    if not data:
        return 0.0
    s = sorted(data)
    idx = int(p / 100 * len(s))
    # Cap index to avoid IndexError for p=100
    idx = min(idx, len(s) - 1)
    return s[idx]


async def main() -> None:
    # Use a unique database for the benchmark
    os.environ["SURREAL_DB"] = f"bench_{uuid.uuid4().hex[:12]}"

    print(f"Connecting to SurrealDB (DB: {os.environ['SURREAL_DB']})...")
    client = await connect()
    await apply_migrations(client)
    
    store = SurrealMessageStore(client)
    conv_id = f"conv_{uuid.uuid4().hex[:8]}"
    
    # 1. Seeding 1,000 messages and measure append latency
    print(f"Seeding 1,000 messages in conversation {conv_id}...")
    append_times = []
    
    for i in range(1000):
        # Mix size ~200-2000 chars
        length = random.randint(200, 2000)
        text = _generate_text(length)
        
        t0 = time.perf_counter()
        await store.append(conv_id, text, lane="message", author="user")
        t1 = time.perf_counter()
        append_times.append((t1 - t0) * 1000) # in ms
        
        if (i + 1) % 100 == 0:
            print(f"  Appended {i + 1}/1000 messages...")
            
    # 2. Warm up with 10 snapshot() calls
    print("Warming up with 10 snapshot() calls...")
    for _ in range(10):
        await store.snapshot(conv_id)
        
    # 3. Measure 200 snapshot() calls
    print("Measuring 200 snapshot() calls...")
    snapshot_times = []
    for _ in range(200):
        t0 = time.perf_counter()
        snap = await store.snapshot(conv_id)
        t1 = time.perf_counter()
        snapshot_times.append((t1 - t0) * 1000) # in ms
        
        # Sanity check
        if len(snap.messages) != 1000:
            print(f"WARNING: Expected 1000 messages, got {len(snap.messages)}")

    # 4. Print results
    print("\n" + "=" * 50)
    print("BENCHMARK RESULTS")
    print("=" * 50)
    print(f"Message Count: 1000")
    print(f"SurrealDB Mode: memory (implied by local setup/URL)")
    print("-" * 50)
    print(f"{'Metric':<15} | {'Append (ms)':<15} | {'Snapshot (ms)':<15}")
    print("-" * 50)
    print(f"{'p50':<15} | {_percentile(append_times, 50):<15.2f} | {_percentile(snapshot_times, 50):<15.2f}")
    print(f"{'p95':<15} | {_percentile(append_times, 95):<15.2f} | {_percentile(snapshot_times, 95):<15.2f}")
    print(f"{'p99':<15} | {_percentile(append_times, 99):<15.2f} | {_percentile(snapshot_times, 99):<15.2f}")
    print(f"{'max':<15} | {max(append_times):<15.2f} | {max(snapshot_times):<15.2f}")
    print("=" * 50)
    
    snapshot_p95 = _percentile(snapshot_times, 95)
    print(f"\nVerdict: snapshot p95 = {snapshot_p95:.2f} ms")
    if snapshot_p95 < 100:
        print("RESULT: SurrealDB CONFIRMED (p95 < 100ms)")
    else:
        print("RESULT: FAIL (p95 >= 100ms) - Notify Architect to initiate pgvector fallback")


if __name__ == "__main__":
    asyncio.run(main())
