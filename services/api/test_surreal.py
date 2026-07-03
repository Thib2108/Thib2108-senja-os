import asyncio
from surrealdb import AsyncSurreal

async def main():
    client = AsyncSurreal("ws://127.0.0.1:8000/rpc")
    await client.connect()
    await client.signin({"username": "root", "password": "root"})
    await client.use("senja", "test")
    
    # Clean up
    # Clean up (skipped)
    
    query1 = """
    BEGIN TRANSACTION;
    LET $a = 1;
    RETURN $a;
    COMMIT TRANSACTION;
    """
    res1 = await client.query(query1)
    print("RES1:", res1)
    
    query2 = """
    BEGIN TRANSACTION;
    LET $a = 2;
    $a;
    COMMIT TRANSACTION;
    """
    res2 = await client.query(query2)
    print("RES2:", res2)

    query3 = """
    LET $id = type::record('intent_log', 'test_key');
    INSERT IGNORE INTO intent_log (id, status) VALUES ($id, 'pending');
    
    BEGIN TRANSACTION;
    LET $current = SELECT VALUE status FROM $id;
    LET $res = IF (array::len($current) > 0 AND $current[0] = 'pending')
        THEN (UPDATE $id SET status = 'claimed' RETURN AFTER)
        ELSE []
        END;
    $res;
    COMMIT TRANSACTION;
    """
    res3 = await client.query(query3)
    print("RES3:", res3)
    
asyncio.run(main())
