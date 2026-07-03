# Agent operating rules — senja-os

1. **Specs are the source of truth.** The SDAI spec set (Notion: SDAI-CHAT-001..004) and the binding contracts (taxonomy pages + Edge Registry v0.2) decide structure, names, and invariants. When code and spec disagree, the spec wins; if the spec is wrong, change the spec first (changelog bump required).
2. **Never invent relation names.** `packages/contracts/src/contracts/edges.py` is generated vocabulary. New edge ⇒ Edge Registry change first, regenerate second.
3. **Never copy the kernel.** Grounding gates, bounded loops, decision log live in `packages/harness_kernel` and are imported by both the chat harness and the knowledge pipelines (004 ADR-04). A second implementation of the verbatim gate is a defect.
4. **No SurrealQL outside `services/api/db/`.** All persistence goes through `repos/ports.py`.
5. **Harvesting from `document-studio`** (read-only quarry): follow `docs/HARVEST.md`. Transplants come in through the spec gate, adapted to this layout, with their tests.
6. **Every slice PR bumps its spec's version** (Block 9 changelog discipline) — CI treats a slice change without a spec change as drift.
