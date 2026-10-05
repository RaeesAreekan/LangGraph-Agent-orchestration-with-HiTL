from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.execution.in_process import InProcessExecutor, InProcessTask
from app.graph.builder import build_graph
from app.observability.events import InMemoryEventSink
from app.schemas.api import TaskRequest
from app.schemas.domain import ApprovalDecision


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
async def test_api_resumes_approval_saved_by_separate_worker_executor():
    task_id = "task-celery-approval"
    record = SimpleNamespace(
        task_id=task_id,
        trace_id="trace-celery-approval",
        status="queued",
        final_answer=None,
        error=None,
        pending_approval=None,
    )
    database = MemoryDatabase(record)
    event_sink = InMemoryEventSink()
    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    worker_executor = InProcessExecutor(
        graph=graph,
        event_sink=event_sink,
        database=database,  # type: ignore[arg-type]
    )
    request = TaskRequest(
        user_id="demo-user",
        task="Prepare a research brief",
        context={},
        human_review_requested=True,
    )

    worker_task = await worker_executor.get(task_id)
    assert worker_task is not None
    await worker_executor.run_existing_task(worker_task, request)
    assert record.status == "waiting_approval"
    assert record.pending_approval is not None

    api_executor = InProcessExecutor(
        graph=graph,
        event_sink=event_sink,
        database=database,  # type: ignore[arg-type]
    )
    api_executor.tasks[task_id] = InProcessTask(
        task_id=task_id,
        trace_id=record.trace_id,
        status="queued",
    )

    resumed = await api_executor.resume(
        task_id,
        ApprovalDecision(
            approval_id=record.pending_approval["approval_id"],
            decision="approve",
            reviewer_id="demo-reviewer",
        ),
    )
    assert resumed.status == "running"

    completed = await api_executor.wait(task_id)

    assert completed.status == "completed"
    assert completed.final_answer is not None
    assert record.status == "completed"


class RecordingDispatcher:
    def __init__(self):
        self.resume_calls = []

    async def enqueue(self, task_id, request):
        pass

    async def enqueue_resume(self, task_id, decision):
        self.resume_calls.append((task_id, decision))


@pytest.mark.asyncio
async def test_resume_queues_celery_resume_instead_of_running_locally():
    task_id = "task-celery-resume"

    record = SimpleNamespace(
        task_id=task_id,
        trace_id="trace-celery-resume",
        status="waiting_approval",
        final_answer=None,
        error=None,
        pending_approval={
            "approval_id": "approval-123",
            "reason": "Human review required",
        },
    )

    database = MemoryDatabase(record)
    dispatcher = RecordingDispatcher()

    executor = InProcessExecutor(
        graph=None,
        event_sink=InMemoryEventSink(),
        database=database,  # type: ignore[arg-type]
        dispatcher=dispatcher,
    )

    decision = ApprovalDecision(
        approval_id="approval-123",
        decision="approve",
        reviewer_id="demo-reviewer",
    )

    resumed = await executor.resume(task_id, decision)

    assert resumed.status == "running"
    assert dispatcher.resume_calls == [
        (task_id, decision),
    ]
    assert task_id not in executor.handles