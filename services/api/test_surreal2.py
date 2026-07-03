import asyncio
from surrealdb import AsyncSurreal

async def main():
    client = AsyncSurreal("ws://127.0.0.1:8000/rpc")
    await client.connect()
    await client.signin({"username": "root", "password": "root"})
    await client.use("senja", "test")
    
    query = """
    LET $counter = (
        UPSERT type::record('conv_counter', 'conv1')
        SET n = IF n THEN n + 1 ELSE 1 END
        RETURN AFTER
    );
    CREATE type::record('message', rand::ulid()) CONTENT {
        conversation: type::record('conversation', 'conv1'),
        author: 'user',
        lane: 'message',
        text: 'hello',
        turn: $counter[0].n
    };
    """
    res = await client.query(query)
    print("RES:", res)
    
asyncio.run(main())
