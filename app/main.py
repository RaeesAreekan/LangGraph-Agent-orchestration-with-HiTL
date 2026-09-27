from fastapi import FastAPI

from app.api.route_tasks import router as tasks_router
from app.config import get_settings
from app.execution.in_process import InProcessExecutor
from app.graph.builder import build_graph
from app.observability.events import InMemoryEventSink

from langgraph.checkpoint.memory import InMemorySaver

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Agent Orchestrator",
        version="0.1.0",
    )

    app.state.settings = settings
    event_sink = InMemoryEventSink()
    graph = build_graph(event_sink=event_sink, checkpointer=InMemorySaver())
    app.state.executor = InProcessExecutor(
        graph=graph,
        event_sink=event_sink,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(tasks_router)

    return app