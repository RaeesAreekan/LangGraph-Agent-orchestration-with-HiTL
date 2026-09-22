from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    analysis_node,
    planning_node,
    research_node,
    review_node,
    synthesis_node,
)
from app.graph.state import OrchestratorState


def build_graph():
    graph = StateGraph(OrchestratorState)

    graph.add_node("planning", planning_node)
    graph.add_node("research", research_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("review", review_node)
    graph.add_node("synthesis", synthesis_node)

    graph.add_edge(START, "planning")

    # These branches execute in parallel.
    graph.add_edge("planning", "research")
    graph.add_edge("planning", "analysis")

    # The review node waits for both branches.
    graph.add_edge("research", "review")
    graph.add_edge("analysis", "review")

    graph.add_edge("review", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()