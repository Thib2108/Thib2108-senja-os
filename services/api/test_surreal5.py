import asyncio
from surrealdb import AsyncSurreal

async def main():
    client = AsyncSurreal("ws://127.0.0.1:8000/rpc")
    await client.connect()
    await client.signin({"username": "root", "password": "root"})
    await client.use("senja", "test")

    claim2 = await client.query("""
    UPDATE type::record('intent_log', string::concat('test', '|', 'ref1'))
    SET status = 'claimed'
    WHERE status = 'pending'
    RETURN AFTER;
    """)
    print("CLAIM2:", claim2)

asyncio.run(main())
