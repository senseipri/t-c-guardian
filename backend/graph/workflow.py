"""
LangGraph workflow definition.

This compiles the node functions into a deterministic, linear
state machine.  The graph topology is:

    [START] ──▶ scrape ──▶ analyze ──▶ [END]

There are NO conditional edges, NO cycles, and NO router functions.
The graph always terminates after exactly two node executions.

The compiled `app` object is imported by main.py and invoked with
`await app.ainvoke(initial_state)`.
"""

from langgraph.graph import StateGraph, END
from backend.graph.state import AgentState
from backend.graph.nodes import scrape_node, analyze_node

workflow = StateGraph(AgentState)

workflow.add_node("scrape", scrape_node)
workflow.add_node("analyze", analyze_node)

workflow.set_entry_point("scrape")
workflow.add_edge("scrape", "analyze")
workflow.add_edge("analyze", END)

app = workflow.compile()