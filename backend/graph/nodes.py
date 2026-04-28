"""
LangGraph node functions.

Each node is a function that receives the full AgentState dict and
returns a PARTIAL dict with only the keys it wants to update.
LangGraph merges the returned dict into the state automatically.
The graph is strictly linear: scrape_node → analyze_node → END.
There are no conditional edges and no loops, so infinite cycling
is structurally impossible.

Error convention:
  - If a node fails, it sets state["error"] to a descriptive string.
  - Downstream nodes check for state["error"] and short-circuit if set.
"""

from backend.graph.state import AgentState
from backend.tools.scraper import scrape_url
from backend.tools.analyzer import analyze_legal_text


async def scrape_node(state: AgentState) -> dict:
    """
    Node 1: Scrape.

    Fetches the URL from state and converts the page to Markdown.
    On success, writes markdown_content.
    On failure, writes error and returns immediately.
    """
    try:
        markdown = await scrape_url(state["url"])

        # Guard: if the page is nearly empty it's probably not a T&C page
        word_count = len(markdown.split())
        if word_count < 10:
            return {
                "markdown_content": "",
                "error": (
                    f"Page has only {word_count} words. "
                    "This doesn't look like a Terms & Conditions page."
                ),
            }

        return {"markdown_content": markdown, "error": None}

    except Exception as exc:
        return {"markdown_content": "", "error": f"Scrape error: {str(exc)}"}


def analyze_node(state: AgentState) -> dict:
    """
    Node 2: Analyze.

    Sends the scraped Markdown to the reasoning LLM and extracts
    structured findings. Short-circuits if a previous node set an error.
    """
    # ── Short-circuit on upstream error ──
    if state.get("error"):
        # Return state unchanged; the error propagates to the API response
        return {"error": state["error"]}

    try:
        analysis = analyze_legal_text(state["markdown_content"])
        return {
            "score": analysis["score"],
            "grade": analysis["grade"],
            "summary": analysis["summary"],
            "findings": analysis["findings"],
            "error": None,
        }

    except Exception as exc:
        return {"error": f"Analysis error: {str(exc)}"}