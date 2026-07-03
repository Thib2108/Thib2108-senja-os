"""Deterministic grounding gates — SDAI-CHAT-001.

The load-bearing invariant: no claim without a resolvable verbatim highlight.
Deterministic by design — no fuzzy matching in this module. Soft signals
(e.g. the S6 entailment checker) live in skills and only ever *flag*; the
hard gate here is what persists or drops.
"""


def verify_verbatim(quote: str, source_text: str, start: int, end: int) -> bool:
    """True iff ``quote`` is exactly ``source_text[start:end]``.

    Satisfies Spec: 003 "highlight verification at write time";
    004 P3 hard gate ("ungrounded atoms are dropped and logged, never persisted").
    Offsets are character offsets into the canonical body text; anyone can re-check.
    """
    if start < 0 or end > len(source_text) or start >= end:
        return False
    return source_text[start:end] == quote
