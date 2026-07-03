"""Shared harness kernel — imported by the chat harness AND the knowledge pipelines.

Never copy these modules (SDAI-CHAT-004 ADR-04: two grounding gates would drift apart).
"""

from harness_kernel.gates import verify_verbatim

__all__ = ["verify_verbatim"]
