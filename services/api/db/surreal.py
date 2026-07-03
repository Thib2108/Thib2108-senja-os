"""SurrealDB engine/session — THE ONLY SurrealQL in the codebase (003 Principle 4).

A static CI check (`test_no_surrealql_outside_db_dir`) keeps this honest.
Local-first: single node, file-backed, bound to 127.0.0.1.

Open question (003 Block 9): embedded (in-process) vs server mode.
"""


class SurrealSession:  # TODO(003-slice): real session + transaction manager
    ...
