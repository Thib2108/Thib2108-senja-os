"""SurrealDB implementation of the repository ports (003 ADR-01).

Transplant note (docs/HARVEST.md): the parity contract-test pattern from the
quarry proves this implementation against in-memory reference stores — port
those tests before implementing, then make them green.
"""

# TODO(003-slice): implement MessageStore, ThreadIndexStore, AtomStore,
# IntentLog, DecisionLog against services/api/db/surreal.py
