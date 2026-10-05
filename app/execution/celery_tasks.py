import asyncio

from app.agents.analyst import AnalystAgent
from app.agents.model import OpenAIStructuredModel
from app.agents.researcher import ResearcherAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.synthesizer import SynthesizerAgent
from app.config import get_settings
from app.execution.celery_app import celery_app
from app.execution.in_process import InProcessExecutor
from app.graph.builder import build_graph
from app.observability.events import PersistentEventSink
from app.persistence.checkpointer import postgres_checkpointer
from app.persistence.database import Database
from app.schemas.api import TaskRequest
from app.memory.factory import create_memory_service

import asyncio
import selectors
import sys

from contextlib import asynccontextmanager

from app.schemas.domain import ApprovalDecision

def run_with_compatible_loop(coro):
    if sys.platform == "win32":
        return asyncio.run(
            coro,
            loop_factory=lambda: asyncio.SelectorEventLoop(
                selectors.SelectSelector()
            ),
        )

    return asyncio.run(coro)

@celery_app.task(
    name="app.execution.celery_tasks.run_workflow",
)
def run_workflow(
    task_id: str,
    request_data: dict,
) -> None:
    run_with_compatible_loop(
        run_workflow_async(
            task_id,
            request_data,
        )
    )

async def run_workflow_async(
    task_id: str,
    request_data: dict,
) -> None:
    request = TaskRequest.model_validate(request_data)

    async with worker_executor() as executor:
        task = await executor.get(task_id)

        if task is None:
            raise KeyError(
                f"Task '{task_id}' was not found."
            )

        await executor.run_existing_task(
            task,
            request,
        )

@celery_app.task(
    name="app.execution.celery_tasks.resume_workflow",
)
def resume_workflow(
    task_id: str,
    decision_data: dict,
) -> None:
    run_with_compatible_loop(
        resume_workflow_async(
            task_id,
            decision_data,
        )
    )

async def resume_workflow_async(
    task_id: str,
    decision_data: dict,
) -> None:
    decision = ApprovalDecision.model_validate(
        decision_data,
    )

    async with worker_executor() as executor:
        task = await executor.get(task_id)

        if task is None:
            raise KeyError(
                f"Task '{task_id}' was not found."
            )

        await executor.run_existing_resume(
            task,
            decision,
        )

        
@asynccontextmanager
async def worker_executor():
    settings = get_settings()
    database = Database(settings.database_url)

    try:
        await database.create_tables()

        event_sink = PersistentEventSink(database)
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

            yield InProcessExecutor(
                graph=graph,
                event_sink=event_sink,
                database=database,
                memory_service=memory_service,
                memory_top_k=settings.memory_top_k,
            )

    finally:
        await database.close()