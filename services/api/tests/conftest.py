import os
import uuid
import pytest
import pytest_asyncio

from repos.memory_impl import MemoryIntentLog, MemoryMessageStore
from repos.surreal_impl import SurrealIntentLog, SurrealMessageStore
from db.surreal import connect, apply_migrations

IMPLS = ["memory", "surreal"]


def _skip_if_pending(param: str) -> None:
    pass  # We handle 'surreal' specifically in the fixtures now


@pytest_asyncio.fixture(params=IMPLS)
async def message_store(request):
    if request.param == "memory":
        return MemoryMessageStore()
    elif request.param == "surreal":
        if "SURREAL_URL" not in os.environ:
            pytest.skip("SURREAL_URL not set")
        
        # Test isolation: unique database name per test
        test_db = f"test_{uuid.uuid4().hex[:12]}"
        os.environ["SURREAL_DB"] = test_db
        
        client = await connect()
        await apply_migrations(client)
        return SurrealMessageStore(client)


@pytest_asyncio.fixture(params=IMPLS)
async def intent_log(request):
    if request.param == "memory":
        return MemoryIntentLog()
    elif request.param == "surreal":
        if "SURREAL_URL" not in os.environ:
            pytest.skip("SURREAL_URL not set")
            
        # Test isolation: unique database name per test
        test_db = f"test_{uuid.uuid4().hex[:12]}"
        os.environ["SURREAL_DB"] = test_db
        
        client = await connect()
        await apply_migrations(client)
        return SurrealIntentLog(client)
