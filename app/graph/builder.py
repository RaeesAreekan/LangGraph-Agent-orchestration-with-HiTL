from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    analysis_node,
    planning_node,
    make_research_node,
    make_review_node,
    synthesis_node,
    route_after_review,
    route_after_approval,
    approval_node,
)
from app.graph.state import OrchestratorState
from app.agents.fake import fake_review
from app.tools.demo_search import DemoSearchTool
from app.tools.registry import ToolRegistry
from app.observability.events import EventSink

from langgraph.checkpoint.base import BaseCheckpointSaver


def build_graph(
    review_fn=fake_review,
    tool_registry: ToolRegistry | None = None,
    event_sink: EventSink | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
):
    if tool_registry is None:
        tool_registry = ToolRegistry(event_sink=event_sink)
        tool_registry.register(DemoSearchTool()) # type: ignore
    graph = StateGraph(OrchestratorState)

    graph.add_node("planning", planning_node)
    graph.add_node("research", make_research_node(tool_registry))
    graph.add_node("analysis", analysis_node)
    graph.add_node("review", make_review_node(review_fn=review_fn))
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("approval", approval_node)

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
            "approval": "approval",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "synthesis": "synthesis",
            "end": END,
        },
    )   
    graph.add_edge("synthesis", END)

    return graph.compile(checkpointer=checkpointer)