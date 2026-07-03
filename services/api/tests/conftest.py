"""Parity fixtures — transplanted pattern from the document-studio quarry.

Every contract test runs over all params. "surreal" skips until surreal_impl
lands; the ADR-01 spike consists of removing that skip and making the identical
suite pass (then the p95<100ms tripwire decides SurrealDB vs pgvector fallback).
"""

import pytest

from repos.memory_impl import MemoryIntentLog, MemoryMessageStore

IMPLS = ["memory", "surreal"]


def _skip_if_pending(param: str) -> None:
    if param == "surreal":
        pytest.skip("surreal_impl pending — the ADR-01 spike flips this on")


@pytest.fixture(params=IMPLS)
def message_store(request):
    _skip_if_pending(request.param)
    return MemoryMessageStore()


@pytest.fixture(params=IMPLS)
def intent_log(request):
    _skip_if_pending(request.param)
    return MemoryIntentLog()
