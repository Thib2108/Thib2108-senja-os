"""SurrealDB engine/session — THE ONLY SurrealQL in the codebase (003 Principle 4).

All SurrealQL string constants used by repos/surreal_impl.py are defined here;
surreal_impl.py imports them and never defines query strings.

Targets SurrealDB 3.x (type::record, HNSW). See the 2.x-to-3.x migration
guide for the renames if this ever runs against an older server.

Connect/migrate pattern:
    client = await connect()
    applied = await apply_migrations(client)
"""

import os
import pathlib
from typing import Any

from surrealdb import AsyncSurreal  # type: ignore[import-untyped]

_MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"

_MIGRATION_INIT_SQL = """
DEFINE TABLE IF NOT EXISTS migration SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS filename ON migration TYPE string;
DEFINE INDEX IF NOT EXISTS migration_filename ON migration FIELDS filename UNIQUE;
"""


async def connect() -> AsyncSurreal:
    """Connect, sign in, and select namespace/database from env vars.

    Defaults (Sprint-01 brief): SURREAL_URL=ws://127.0.0.1:8000/rpc,
    SURREAL_NS=senja, SURREAL_DB=dev, SURREAL_USER/PASS=root/root.
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

    Maintains a `migration` table recording applied filenames; skips files
    already applied. Returns the filenames applied in this call.
    """
    await client.query(_MIGRATION_INIT_SQL)

    applied: list[str] = []
    for path in sorted(_MIGRATIONS_DIR.glob("*.surql")):
        filename = path.name
        existing: Any = await client.query(
            "SELECT filename FROM migration WHERE filename = $fn LIMIT 1",
            {"fn": filename},
        )
        rows: list[Any] = existing if isinstance(existing, list) else []
        if rows:
            continue  # already applied

        sql = path.read_text(encoding="utf-8")
        # The Python SDK rejects empty queries — skip comment-only files.
        has_statements = any(
            line.strip() and not line.strip().startswith("--")
            for line in sql.splitlines()
        )
        if has_statements:
            await client.query(sql)

        await client.create("migration", {"filename": filename})
        applied.append(filename)

    return applied


# ---------------------------------------------------------------------------
# SurrealQL constants — imported by repos/surreal_impl.py
# ---------------------------------------------------------------------------

# Append is ONE transaction: ensure conversation, allocate the turn atomically
# (conv_counter.n has DEFAULT 0 in 0001_core.surql), create the message.
# A crash can never leave an allocated turn without its message (no gaps).
# created_at is stamped by the schema's VALUE time::now() — never supplied here.
SQL_APPEND_MESSAGE = """
BEGIN TRANSACTION;
UPSERT type::record('conversation', $conv_id);
LET $c = (UPSERT type::record('conv_counter', $conv_id) SET n += 1 RETURN AFTER);
CREATE type::record('message', rand::ulid()) CONTENT {
    conversation: type::record('conversation', $conv_id),
    author: $author,
    lane: $lane,
    text: $text,
    turn: $c[0].n
};
COMMIT TRANSACTION;
"""

SQL_SNAPSHOT = """
SELECT * FROM message
WHERE conversation = type::record('conversation', $conv_id)
ORDER BY turn ASC;
"""

# Intent-log: deterministic record id = step|input_ref makes enqueue idempotent.
SQL_ENQUEUE = """
INSERT IGNORE INTO intent_log (id, step, input_ref, status) VALUES (
    type::record('intent_log', string::concat($step, '|', $input_ref)),
    $step,
    $input_ref,
    'pending'
);
"""

# Claim: single-statement conditional update — atomic; RETURN AFTER yields the
# record only for the caller whose WHERE matched (the claim winner).
SQL_CLAIM = """
UPDATE type::record('intent_log', string::concat($step, '|', $input_ref))
SET status = 'claimed'
WHERE status = 'pending'
RETURN AFTER;
"""

SQL_COMPLETE = """
UPDATE type::record('intent_log', string::concat($step, '|', $input_ref))
SET status = 'done';
"""
