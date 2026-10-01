from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    make_analysis_node,
    make_research_node,
    make_review_node,
    make_synthesis_node,
    route_after_review,
    route_after_approval,
    approval_node,
    make_planning_node
)
from app.graph.state import OrchestratorState
from app.agents.fake import fake_review
from app.tools.demo_search import DemoSearchTool
from app.tools.registry import ToolRegistry
from app.observability.events import EventSink
from app.agents.supervisor import SupervisorAgent
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.researcher import ResearcherAgent
from app.tools.mcp_provider import (
    McpSearchTool,
    McpToolProvider,
)
from app.agents.analyst import AnalystAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.synthesizer import SynthesizerAgent

def build_graph(
    review_fn=fake_review,
    tool_registry: ToolRegistry | None = None,
    event_sink: EventSink | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    researcher: ResearcherAgent | None = None,
    supervisor: SupervisorAgent | None = None,
    analyst: AnalystAgent | None = None,
    reviewer: ReviewerAgent | None = None,
    synthesizer: SynthesizerAgent | None = None,
    tool_mode:str = "demo"
):
    if tool_registry is None:
        tool_registry = ToolRegistry(
            event_sink=event_sink,
        )

        if tool_mode == "mcp":
            provider = McpToolProvider.from_connections(
                {
                    "demo_search": {
                        "transport": "stdio",
                        "command": "python",
                        "args": [
                            "-m",
                            "app.tools.mcp_server",
                        ],
                    }
                }
            )

            tool_registry.register(
                McpSearchTool(provider), # type: ignore
            )
        else:
            tool_registry.register(
                DemoSearchTool(), # type: ignore
            )
    graph = StateGraph(OrchestratorState)

    graph.add_node("planning", make_planning_node(supervisor=supervisor))
    graph.add_node("research", make_research_node(tool_registry, researcher=researcher))
    graph.add_node("analysis", make_analysis_node(analyst=analyst))
    graph.add_node("review", make_review_node(review_fn=review_fn, reviewer=reviewer))
    graph.add_node("synthesis", make_synthesis_node(synthesizer=synthesizer))
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