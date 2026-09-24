from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    analysis_node,
    planning_node,
    research_node,
    make_review_node,
    synthesis_node,
    route_after_review,
)
from app.graph.state import OrchestratorState
from app.agents.fake import fake_review

def build_graph(review_fn = fake_review):
    graph = StateGraph(OrchestratorState)

    graph.add_node("planning", planning_node)
    graph.add_node("research", research_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("review", make_review_node(review_fn=review_fn))
    graph.add_node("synthesis", synthesis_node)

    graph.add_edge(START, "planning")

    # These branches execute in parallel.
    graph.add_edge("planning", "research")
    graph.add_edge("planning", "analysis")

    # The review node waits for both branches.
    graph.add_edge("research", "review")
    graph.add_edge("analysis", "review")

    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "research": "research",
            "synthesis": "synthesis",
            "analysis": "analysis",
            "end": END,
        },
    )

    graph.add_edge("synthesis", END)

    return graph.compile()