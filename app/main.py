from fastapi import FastAPI

from app.api.route_tasks import router as tasks_router
from app.config import get_settings
from app.execution.in_process import InProcessExecutor
from app.graph.builder import build_graph
from app.observability.events import InMemoryEventSink

from langgraph.checkpoint.memory import InMemorySaver

from app.agents.model import OpenAIStructuredModel
from app.agents.researcher import ResearcherAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.analyst import AnalystAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.synthesizer import SynthesizerAgent

def create_app() -> FastAPI:
    settings = get_settings()

    researcher = None
    supervisor = None
    analyst = None
    reviewer = None
    synthesizer = None
    model = OpenAIStructuredModel(settings)

    if settings.agent_mode == "live":
        researcher = ResearcherAgent(
            model=model,
        )
        supervisor = SupervisorAgent(
            model=model,  
        )
        analyst = AnalystAgent(
            model=model,
        )
        reviewer = ReviewerAgent(
            model=model,
        )
        synthesizer = SynthesizerAgent(
            model=model,
        )

    app = FastAPI(
        title="Agent Orchestrator",
        version="0.1.0",
    )

    app.state.settings = settings
    event_sink = InMemoryEventSink()
    graph = build_graph(event_sink=event_sink, checkpointer=InMemorySaver(), researcher=researcher, supervisor=supervisor, analyst=analyst, synthesizer=synthesizer, reviewer=reviewer)
    app.state.executor = InProcessExecutor(
        graph=graph,
        event_sink=event_sink,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(tasks_router)

    return app