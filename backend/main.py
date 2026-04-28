"""
FastAPI entry point for T&C Guardian.

This file does three things:
  1. Configures CORS so the Chrome Extension can call localhost:8000
  2. Defines the POST /scan endpoint that triggers the LangGraph pipeline
  3. Translates graph errors into proper HTTP error responses

Run with:
    uvicorn backend.main:app --reload
"""
import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.graph.workflow import app as graph_app

    
    
# ── FastAPI app ──
app = FastAPI(
    title="T&C Guardian",
    version="1.0.0",
    description="AI-powered Terms & Conditions scanner",
)

# ── CORS ──
# Chrome extensions make requests from a chrome-extension:// origin.
# During development we also allow localhost.  In production, replace
# the wildcard with your specific extension ID origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request model ──
class ScanRequest(BaseModel):
    url: str


# ── Health check ──
@app.get("/health")
async def health():
    """Simple liveness probe."""
    return {"status": "ok", "service": "tc-guardian"}


# ── Main scan endpoint ──
@app.post("/scan")
async def scan_url(req: ScanRequest):
    """
    Accept a URL, run the LangGraph pipeline (Scrape → Analyze),
    and return the structured harm report.

    Returns 400 if any pipeline node fails.
    """
    # Validate URL minimally
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://",
        )

    # Invoke the compiled LangGraph
    # The initial state only needs the url key; all other keys
    # are populated by the nodes.
    initial_state = {
        "url": req.url,
        "markdown_content": "",
        "findings": [],
        "score": 0,
        "grade": "",
        "summary": "",
        "error": None,
    }

    final_state = await graph_app.ainvoke(initial_state)

    # ── Error handling ──
    if final_state.get("error"):
        raise HTTPException(status_code=400, detail=final_state["error"])

    # ── Success response ──
    return {
        "score": final_state["score"],
        "grade": final_state["grade"],
        "summary": final_state["summary"],
        "findings": final_state["findings"],
    }