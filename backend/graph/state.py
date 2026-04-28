"""
Defines the shared state dictionary that flows through every node
in the LangGraph pipeline. Using TypedDict gives us type safety
without the overhead of Pydantic inside the graph.

Every key here is readable and writable by any node.
Optional fields use None as their default so downstream nodes
can check whether upstream work succeeded or failed.
"""

from typing import TypedDict, Optional


class AgentState(TypedDict):
    # INPUT: the URL the user wants scanned
    url: str

    # AFTER SCRAPE NODE: raw markdown of the page
    markdown_content: str

    # AFTER ANALYZE NODE: structured results
    findings: list          # list of finding dicts
    score: int              # 0-100 safety score
    grade: str              # A through F
    summary: str            # one-line human summary

    # ERROR TRACKING: set by any node that fails
    error: Optional[str]