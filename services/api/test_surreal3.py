import asyncio
from surrealdb import AsyncSurreal

async def main():
    client = AsyncSurreal("ws://127.0.0.1:8000/rpc")
    await client.connect()
    await client.signin({"username": "root", "password": "root"})
    await client.use("senja", "test")
    
    # Ensure conversation
    await client.query("UPSERT type::record('conversation', 'conv1') SET id = type::record('conversation', 'conv1');")
    
    # 1. Allocate turn
    counter_sql = """
    UPSERT type::record('conv_counter', 'conv1') 
    SET n = IF n THEN n + 1 ELSE 1 END
    RETURN AFTER;
    """
    counter_res = await client.query(counter_sql)
    print("COUNTER:", counter_res)
    
    if isinstance(counter_res, list) and len(counter_res) > 0:
        turn = counter_res[0].get("n", 1)
    else:
        turn = 1
        
    print("TURN:", turn)
    
    # 2. Create message
    msg_sql = """
    CREATE type::record('message', rand::ulid()) CONTENT {
        conversation: type::record('conversation', 'conv1'),
        author: 'user',
        lane: 'message',
        text: 'hello',
        turn: $turn
    };
    """
    msg_res = await client.query(msg_sql, {"turn": turn})
    print("MSG:", msg_res)

asyncio.run(main())
