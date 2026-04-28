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

# ── Build the graph ──
workflow = StateGraph(AgentState)

# Register nodes
workflow.add_node("scrape", scrape_node)
workflow.add_node("analyze", analyze_node)

# Wire the linear pipeline
workflow.set_entry_point("scrape")
workflow.add_edge("scrape", "analyze")
workflow.add_edge("analyze", END)

# Compile into a runnable LangGraph application
app = workflow.compile()