"""Static purity checks — gates that fail, not remind (003 Block 9)."""

import pathlib

# Markers that indicate SurrealQL leaked outside db/ (003 Principle 4).
_SURQL_TOKENS = (
    "DEFINE TABLE",
    "DEFINE FIELD",
    "DEFINE INDEX",
    "BEGIN TRANSACTION",
    "COMMIT TRANSACTION",
    "type::record(",
    "type::thing(",
    "INSERT IGNORE",
    "RELATE ",
)


def test_no_surrealql_outside_db_dir():
    """003 Block 7 #3 (P4): the repository port is the only seam — no query
    strings anywhere but services/api/db/."""
    root = pathlib.Path(__file__).resolve().parents[1]  # services/api
    offenders = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if rel.parts[0] in {"db", "tests"}:
            continue
        if any(part in {".venv", "__pycache__"} for part in rel.parts):
            continue
        content = path.read_text(encoding="utf-8")
        hits = [tok for tok in _SURQL_TOKENS if tok in content]
        if hits:
            offenders.append(f"{rel}: {hits}")
    assert not offenders, f"SurrealQL leaked outside db/ (003 Principle 4): {offenders}"
