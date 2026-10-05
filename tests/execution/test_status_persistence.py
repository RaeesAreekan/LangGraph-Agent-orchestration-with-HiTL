from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.execution.in_process import InProcessExecutor, InProcessTask
from app.graph.builder import build_graph
from app.observability.events import InMemoryEventSink
from app.schemas.api import TaskRequest


class MemoryDatabase:
    def __init__(self, record):
        self.record = record

    @asynccontextmanager
    async def session(self):
        yield self

    async def get(self, model, task_id):
        if task_id == self.record.task_id:
            return self.record
        return None

    async def commit(self):
        pass


@pytest.mark.asyncio
async def test_worker_completion_is_persisted_and_visible_to_api_executor():
    task_id = "task-celery-status"
    record = SimpleNamespace(
        task_id=task_id,
        trace_id="trace-celery-status",
        status="queued",
        final_answer=None,
        error=None,
        pending_approval=None,
    )
    database = MemoryDatabase(record)
    event_sink = InMemoryEventSink()
    worker_executor = InProcessExecutor(
        graph=build_graph(),
        event_sink=event_sink,
        database=database, # type: ignore
    )
    request = TaskRequest(
        user_id="demo-user",
        task="Prepare a research brief",
        context={},
    )

    worker_task = await worker_executor.get(task_id)
    assert worker_task is not None
    await worker_executor.run_existing_task(worker_task, request)

    api_executor = InProcessExecutor(database=database) # type: ignore
    api_executor.tasks[task_id] = InProcessTask(
        task_id=task_id,
        trace_id=record.trace_id,
        status="queued",
    )
    status_task = await api_executor.get(task_id)

    assert record.status == "completed"
    assert record.final_answer is not None
    assert status_task is not None
    assert status_task.status == "completed"
    assert any(
        event.event_type == "task_completed"
        for event in event_sink.events
    )