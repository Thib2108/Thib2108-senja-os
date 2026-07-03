import asyncio
from surrealdb import AsyncSurreal

async def main():
    client = AsyncSurreal("ws://127.0.0.1:8000/rpc")
    await client.connect()
    await client.signin({"username": "root", "password": "root"})
    await client.use("senja", "test")
    
    # 1. Enqueue
    enq = await client.query("""
    INSERT IGNORE INTO intent_log (id, step, input_ref, status) VALUES (
        type::record('intent_log', string::concat('test', '|', 'ref1')),
        'test',
        'ref1',
        'pending'
    );
    """)
    print("ENQ:", enq)
    
    # 2. Check if it exists
    sel = await client.query("SELECT * FROM intent_log;")
    print("SEL:", sel)

    # 3. Claim
    claim = await client.query("""
    UPDATE type::record('intent_log', string::concat('test', '|', 'ref1'))
    SET status = 'claimed'
    WHERE status = 'pending'
    RETURN AFTER;
    """)
    print("CLAIM:", claim)
    
asyncio.run(main())
