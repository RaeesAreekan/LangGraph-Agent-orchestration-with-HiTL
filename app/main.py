from fastapi import FastAPI

from app.api.route_tasks import router as tasks_router
from app.config import get_settings,Settings
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

from contextlib import asynccontextmanager
from app.persistence.checkpointer import postgres_checkpointer

def create_app(settings: Settings) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        event_sink = InMemoryEventSink()

        researcher = None
        supervisor = None
        analyst = None
        reviewer = None
        synthesizer = None

        if settings.agent_mode == "live":
            model = OpenAIStructuredModel(settings)

            researcher = ResearcherAgent(model=model)
            supervisor = SupervisorAgent(model=model)
            analyst = AnalystAgent(model=model)
            reviewer = ReviewerAgent(model=model)
            synthesizer = SynthesizerAgent(model=model)

        if settings.checkpoint_backend == "postgres":
            async with postgres_checkpointer(
                settings.database_url,
            ) as checkpointer:
                graph = build_graph(
                    event_sink=event_sink,
                    checkpointer=checkpointer,
                    researcher=researcher,
                    supervisor=supervisor,
                    analyst=analyst,
                    reviewer=reviewer,
                    synthesizer=synthesizer,
                    tool_mode=settings.tool_mode,
                    brave_api_key=settings.brave_api_key,
                )

                app.state.executor = InProcessExecutor(
                    graph=graph,
                    event_sink=event_sink,
                )

                yield

        else:
            graph = build_graph(
                event_sink=event_sink,
                checkpointer=InMemorySaver(),
                researcher=researcher,
                supervisor=supervisor,
                analyst=analyst,
                reviewer=reviewer,
                synthesizer=synthesizer,
                tool_mode=settings.tool_mode,
                brave_api_key=settings.brave_api_key,
            )

            app.state.executor = InProcessExecutor(
                graph=graph,
                event_sink=event_sink,
            )

            yield
    app = FastAPI(
    title="Agent Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
    )     
    app.state.settings = settings


    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(tasks_router)

    return app