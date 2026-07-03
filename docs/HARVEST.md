# Harvest rules — the document-studio quarry

`Thib2108/document-studio` (Sprint 0–2 predecessor) is kept **read-only** as a reference.
It is never merged, never remoted-in, never refactored in place.

## The gate

A file may be transplanted only if it earns its place under SDAI-CHAT-001/003/004:
right concern, right layer, no competing twin left behind. Transplants are adapted to
this repo's layout and arrive **with their tests** in the same commit.

## Sanctioned transplant list (initial)

| What | From | Why it survives |
| --- | --- | --- |
| Storage port + parity contract-test pattern | `apps/api` (VectorStorePort / GraphStorePort / EmbedderPort + parity tests) | This is the mechanism the 003 ADR-01 tripwire runs on: SurrealDB vs pgvector fallback is decided by port tests, and the pattern already proves adapters against in-memory references |
| Ollama embedder adapter (L2-normalized) | `apps/api` | Route-agnostic; survives 001 ADR-06 unchanged |
| ONBOARDING.md discipline (clone → running → first test < 30 min, verified commands) | repo root | Process, not code — rewrite for this stack |

## Retired (do not transplant)

- `apps/agent` (Node Fastify orchestrator) — competes with `packages/harness_kernel` (004 ADR-04).
- Kuzu + sqlite-vec adapters — 003 ADR-01 chose SurrealDB; pgvector is the designated fallback, not sqlite-vec.
- `apps/` flat layout, ad-hoc edge/tag handling — superseded by the Edge Registry and this layout.
