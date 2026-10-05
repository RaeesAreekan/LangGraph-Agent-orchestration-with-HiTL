from fastapi import FastAPI

from app.api.route_tasks import router as tasks_router
from app.config import get_settings,Settings
from app.execution.in_process import InProcessExecutor
from app.graph.builder import build_graph
from app.observability.events import InMemoryEventSink,PersistentEventSink

from langgraph.checkpoint.memory import InMemorySaver

from app.agents.model import OpenAIStructuredModel
from app.agents.researcher import ResearcherAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.analyst import AnalystAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.synthesizer import SynthesizerAgent

from contextlib import asynccontextmanager
from app.persistence.checkpointer import postgres_checkpointer
from app.persistence.database import Database

from app.execution.dispatcher import CeleryTaskDispatcher

from app.memory.factory import create_memory_service

def create_app(settings: Settings|None = None) -> FastAPI:
    settings = settings or get_settings()

    dispatcher = (
    CeleryTaskDispatcher()
    if settings.execution_backend == "celery"
    else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        event_sink = InMemoryEventSink()
    
        memory_service = create_memory_service(settings)

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
            database = Database(settings.database_url)
            await database.create_tables()

            event_sink = PersistentEventSink(database)
            try:
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
                        database=database,
                        dispatcher=dispatcher,
                        memory_service=memory_service,
                        memory_top_k=settings.memory_top_k,
                    )

                    yield
            finally:
                await database.close()

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
                memory_service=memory_service,
                memory_top_k=settings.memory_top_k,
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