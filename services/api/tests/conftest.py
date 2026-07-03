"""Parity fixtures — identical contract tests run over every implementation.

- memory: always runs; repos/memory_impl.py defines correct behavior.
- surreal: runs when SURREAL_URL is set (CI sets it; locally requires a
  running SurrealDB). Each test gets a fresh isolated database, so tests
  never see each other's data.
"""

import os
import uuid

import pytest

from repos.memory_impl import MemoryIntentLog, MemoryMessageStore

IMPLS = ["memory", "surreal"]


async def _surreal_client():
    if not os.environ.get("SURREAL_URL"):
        pytest.skip("SURREAL_URL not set — start SurrealDB to run surreal params")
    from db.surreal import apply_migrations, connect

    client = await connect()
    # per-test isolation: fresh database, migrations applied from scratch
    ns = os.environ.get("SURREAL_NS", "senja")
    await client.use(ns, f"t_{uuid.uuid4().hex[:12]}")
    await apply_migrations(client)
    return client


@pytest.fixture(params=IMPLS)
async def message_store(request):
    if request.param == "memory":
        yield MemoryMessageStore()
        return
    client = await _surreal_client()
    from repos.surreal_impl import SurrealMessageStore

    try:
        yield SurrealMessageStore(client)
    finally:
        await client.close()


@pytest.fixture(params=IMPLS)
async def intent_log(request):
    if request.param == "memory":
        yield MemoryIntentLog()
        return
    client = await _surreal_client()
    from repos.surreal_impl import SurrealIntentLog

    try:
        yield SurrealIntentLog(client)
    finally:
        await client.close()
