"""FastAPI wiring, SSE fan-out, auth middleware — SDAI-CHAT-003 Block 6.

STRIDE controls at this layer: bind 127.0.0.1, per-install bearer token on every
route, payload rejection for server-stamped fields.
"""

from fastapi import FastAPI

app = FastAPI(title="senja-os api")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
