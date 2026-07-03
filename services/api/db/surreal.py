"""SurrealDB engine/session — THE ONLY SurrealQL in the codebase (003 Principle 4).

A static CI check (`test_no_surrealql_outside_db_dir`) keeps this honest.
Local-first: single node, in-memory server, bound to 127.0.0.1.

Connect/migrate pattern:
    client = await connect()
    applied = await apply_migrations(client)

All SurrealQL string constants used by repos/surreal_impl.py are defined here.
"""

import os
import pathlib
from typing import Any

from surrealdb import AsyncSurreal  # type: ignore[import-untyped]

_MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"

# ---------------------------------------------------------------------------
# Migration DDL
# ---------------------------------------------------------------------------

_MIGRATION_INIT_SQL = """
DEFINE TABLE IF NOT EXISTS migration SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS filename ON migration TYPE string;
DEFINE INDEX IF NOT EXISTS migration_filename ON migration FIELDS filename UNIQUE;
"""

# Schemaless tables used by the implementation that are not in the .surql files
_EXTRA_DDL = """
DEFINE TABLE IF NOT EXISTS conv_counter SCHEMALESS;
DEFINE TABLE IF NOT EXISTS conversation SCHEMALESS;
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def connect() -> AsyncSurreal:
    """Connect to SurrealDB, sign in, and select the namespace/database.

    Reads configuration from environment variables with the defaults specified
    in the Sprint-01 brief:

        SURREAL_URL  = ws://127.0.0.1:8000/rpc
        SURREAL_NS   = senja
        SURREAL_DB   = dev
        SURREAL_USER = root
        SURREAL_PASS = root
    """
    url = os.environ.get("SURREAL_URL", "ws://127.0.0.1:8000/rpc")
    ns = os.environ.get("SURREAL_NS", "senja")
    db = os.environ.get("SURREAL_DB", "dev")
    user = os.environ.get("SURREAL_USER", "root")
    password = os.environ.get("SURREAL_PASS", "root")

    client = AsyncSurreal(url)
    await client.connect()
    await client.signin({"username": user, "password": password})
    await client.use(ns, db)
    return client


async def apply_migrations(client: AsyncSurreal) -> list[str]:
    """Execute *.surql files in filename order, idempotently.

    Maintains a `migration` table recording applied filenames.  Skips any
    file that has already been applied.  Returns the list of filenames that
    were applied in this call (empty list if nothing was new).
    """
    # Ensure the migration tracking table exists.
    await client.query(_MIGRATION_INIT_SQL)

    # Ensure runtime helper tables (schemaless) exist.
    await client.query(_EXTRA_DDL)

    applied: list[str] = []

    surql_files = sorted(_MIGRATIONS_DIR.glob("*.surql"))
    for path in surql_files:
        filename = path.name

        # Check whether this migration was already applied.
        existing: Any = await client.query(
            "SELECT filename FROM migration WHERE filename = $fn LIMIT 1",
            {"fn": filename},
        )
        # query() returns a list of records for a single statement.
        rows: list[Any] = existing if isinstance(existing, list) else []
        if rows:
            continue  # already applied

        sql = path.read_text(encoding="utf-8")
        # The Python SDK crashes on empty queries, so skip if file is only comments
        has_statements = any(
            line.strip() and not line.strip().startswith("--") 
            for line in sql.splitlines()
        )
        if has_statements:
            await client.query(sql)

        # Record the migration as applied.
        await client.create("migration", {"filename": filename})
        applied.append(filename)

    return applied


# ---------------------------------------------------------------------------
# SurrealQL constants — called by repos/surreal_impl.py
# All query strings live here; surreal_impl.py imports them, never defines them.
# ---------------------------------------------------------------------------

# Ensure a conversation record exists (message.conversation is record<conversation>).
SQL_ENSURE_CONV = """
UPSERT type::record('conversation', $conv_id)
SET id = type::record('conversation', $conv_id)
RETURN NONE;
"""

# Atomic turn allocation + message creation in one transaction.
#
# Strategy:
#   1. UPSERT the counter record, incrementing n atomically.
#   2. Read back the new n — this is the allocated turn.
#   3. CREATE the message with that turn.
#   4. RETURN the message so the caller can build a Message model.
#
# Using BEGIN/COMMIT ensures no concurrent writer can read the same n value.
# The RETURN AFTER on the UPSERT is what makes n available inside the txn.
SQL_ATOMIC_APPEND = """
BEGIN TRANSACTION;
LET $counter = (
    UPSERT type::record('conv_counter', $conv_id)
    SET n = IF (array::len(SELECT VALUE n FROM type::record('conv_counter', $conv_id)) > 0)
              THEN (SELECT VALUE n FROM type::record('conv_counter', $conv_id))[0] + 1
              ELSE 1 END
    RETURN AFTER
);
LET $turn = $counter[0].n;
LET $created = (
    CREATE message CONTENT {
        conversation: type::record('conversation', $conv_id),
        author: $author,
        lane: $lane,
        text: $text,
        turn: $turn
    }
);
RETURN $created[0];
COMMIT TRANSACTION;
"""

# Snapshot: all messages for a conversation, ordered by turn.
SQL_SNAPSHOT = """
SELECT * FROM message
WHERE conversation = type::record('conversation', $conv_id)
ORDER BY turn ASC;
"""

# Intent-log: insert a pending entry; no-op if (step, input_ref) key already exists.
SQL_ENQUEUE = """
INSERT IGNORE INTO intent_log (id, step, input_ref, status) VALUES (
    type::record('intent_log', string::concat($step, '|', $input_ref)),
    $step,
    $input_ref,
    'pending'
);
"""

# Claim: atomically transition pending → claimed; return the updated record if
# successful so the caller knows whether they won the race.
SQL_CLAIM = """
BEGIN TRANSACTION;
LET $id = type::record('intent_log', string::concat($step, '|', $input_ref));
LET $current = SELECT VALUE status FROM $id;
LET $updated = IF (array::len($current) > 0 AND $current[0] = 'pending')
    THEN (UPDATE $id SET status = 'claimed' RETURN AFTER)
    ELSE []
    END;
RETURN $updated;
COMMIT TRANSACTION;
"""

# Complete: mark the entry as done.
SQL_COMPLETE = """
UPDATE type::record('intent_log', string::concat($step, '|', $input_ref))
SET status = 'done';
"""
