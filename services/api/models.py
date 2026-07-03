"""Runtime models for the store slice — SDAI-CHAT-003 Block 5 shared language.

Server-stamped fields (id, turn, created_at) are set ONLY by store
implementations — never accepted from clients or models (003 Principle 3).
"""

from datetime import datetime

from pydantic import BaseModel

MAX_MESSAGE_BYTES = 262_144  # 256 KB — cap counts BYTES, not chars (Block 7 test #1)


class MessageTooLarge(ValueError):
    """Maps to HTTP 413 at the API edge — never truncate silently."""


class Message(BaseModel):
    id: str
    conversation_id: str
    author: str  # "user" | "assistant"
    lane: str    # "message" | "cot" | "todo" | "tool"
    text: str
    turn: int                # server-stamped, monotonic per conversation
    created_at: datetime     # server-stamped


class Snapshot(BaseModel):
    """Immutable read for the harness — a copy, never a live reference."""

    conversation_id: str
    messages: list[Message]
