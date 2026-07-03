# Senja OS

Spec-driven monorepo: AI chatbox, harness kernel, and document intelligence.

**The source of truth is the SDAI spec set in Notion — not this README.**

| Spec | Owns |
| --- | --- |
| SDAI-CHAT-001 · Harness | Orchestration, skills, bounded loops, grounding gates, model tiers (ADR-06: Pydantic AI over LiteLLM base-URL) |
| SDAI-CHAT-002 · UI Shell | The four-surface chatbox UI |
| SDAI-CHAT-003 · Backend | SurrealDB store of record, API seam, SSE, idempotency |
| SDAI-CHAT-004 · Document Intelligence | P1–P5 pipelines: ingest, facets, atomize, topology, trust |
| Taxonomies + Edge Registry (v0.2) | Binding contracts — loaded as versioned inputs, never pasted into prompts |

## Layout

```
packages/
  harness_kernel/     # loops · gates · binding · decisions — shared kernel (004 ADR-04)
  contracts/          # typed I/O; enums GENERATED from taxonomies + Edge Registry
services/api/
  app.py              # FastAPI wiring, SSE fan-out, auth middleware
  db/                 # surreal.py + migrations — the ONLY SurrealQL in the codebase
  repos/              # ports.py (swap seam) + surreal_impl.py
  events.py           # atomic write+event, monotonic turns, SSE resume
  gatesvc.py          # write-time gates (backend half of the grounding contract)
  embeddings.py       # Ollama vectors, never blocks the append path
  knowledge/          # adapters · pipelines p1–p5 · contracts · ontology_loader
apps/web/src/chatbox/ # SDAI-CHAT-002 surface
```

## Invariants (gates that fail, not remind)

1. Messages are append-only and immutable — no update path exists, anywhere.
2. Edges only from the Edge Registry — an ad-hoc relation name is a CI failure.
3. No claim without a resolvable verbatim highlight (deterministic gate, shared kernel).
4. No SurrealQL outside `services/api/db/` — the store is swappable behind ports.
5. No file-type branch below the waist — file type changes the adapter, never the spine.
6. Every effectful step is idempotent — intent log consulted before re-execution.
7. The server stamps ids, turns, timestamps, and provenance — clients and models cannot.

## Predecessor

`Thib2108/document-studio` is a **read-only quarry** — see `docs/HARVEST.md`. Nothing enters this repo unless it earns its place under the spec set.
