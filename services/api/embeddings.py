"""Ollama embedding calls (vectors only) — never blocks the append path (003 Block 6).

Transplant candidate (docs/HARVEST.md): the quarry's L2-normalized OllamaEmbedder
is route-agnostic and survives 001 ADR-06 unchanged.
"""


async def embed(text: str) -> list[float]:  # TODO(003-slice): 768-dim, async, non-blocking
    raise NotImplementedError
