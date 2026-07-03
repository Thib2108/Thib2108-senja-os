"""Decision log — record-once / replay-many cognition (003 ADR-03, 004 shared contract).

Every model call is logged with stage, model tier, tokens, and outcome.
Non-deterministic cognition becomes replayable because decisions are immutable events.
"""

from datetime import datetime

from pydantic import BaseModel


class DecisionRecord(BaseModel):
    id: str
    stage: str
    model_tier: str          # e.g. "e4b" | "12b" | "cloud-reduce"
    tokens_in: int
    tokens_out: int
    outcome: str
    ts: datetime
