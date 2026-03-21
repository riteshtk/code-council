"""CodeCouncil API server."""

from fastapi import FastAPI

app = FastAPI(
    title="CodeCouncil",
    description="AI agent council for codebase intelligence",
    version="0.1.0",
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
