"""Bounded loops — SDAI-CHAT-001.

Every model-in-the-loop iteration runs under an explicit budget (iterations,
tokens, wall-clock). Unbounded loops are a defect, not a tuning problem.

TODO(001-slice): port the loop policy from the harness spec once the first
skill lands; keep this module dependency-free.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoopBudget:
    max_iterations: int
    max_tokens: int | None = None
    max_seconds: float | None = None
