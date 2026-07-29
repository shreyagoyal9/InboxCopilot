"""
InboxCopilot backend — FastAPI app.

Why FastAPI (Python) over Node/Express for this project:
- Gmail API's official Python client is the most mature/well-documented option.
- The batch-relevance extraction step (Task 7) will likely use regex now and
  may swap in an LLM call later — Python's text-processing ecosystem is a
  natural fit either way.
- FastAPI deploys cleanly to Cloud Run as a container with minimal config,
  and gives us free request validation + auto docs (/docs) for development.
"""

from fastapi import FastAPI

app = FastAPI(title="InboxCopilot API")


@app.get("/health")
def health():
    """Basic health check endpoint so we can confirm Cloud Run deploys are alive."""
    return {"status": "ok", "service": "InboxCopilot"}
