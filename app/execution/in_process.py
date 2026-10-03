import asyncio
from dataclasses import dataclass
from unittest import result
from uuid import uuid4

from app.graph.builder import build_graph
from app.schemas.api import TaskRequest
from app.schemas.domain import FinalAnswer

from app.observability.events import (
    EventSink,
    InMemoryEventSink,
)
from app.schemas.domain import ExecutionEvent,ApprovalDecision
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig

@dataclass
class InProcessTask:
    task_id: str
    trace_id: str
    status: str
    final_answer: FinalAnswer | None = None
    error: str | None = None
    pending_approval: dict | None = None


class InProcessExecutor:
    def __init__(self, graph=None,event_sink: EventSink | None = None,) -> None:
        self.event_sink = event_sink or InMemoryEventSink()
        self.graph = graph or build_graph(event_sink=self.event_sink)
        self.tasks: dict[str, InProcessTask] = {}
        self.handles: dict[str, asyncio.Task] = {}

    async def _emit(
        self,
        task_id: str,
        trace_id: str,
        event_type: str,
        component: str,
        status: str,
        summary: str,
        metadata: dict | None = None,
    ) -> None:
        await self.event_sink.append(
            ExecutionEvent(
                task_id=task_id,
                trace_id=trace_id,
                event_type=event_type,
                component=component,
                status=status,
                summary=summary,
                metadata=metadata or {},
            )
        )

    async def submit(self, request: TaskRequest) -> InProcessTask:
        task_id = str(uuid4())
        trace_id = str(uuid4())

        task = InProcessTask(
            task_id=task_id,
            trace_id=trace_id,
            status="queued",
        )

        await self._emit(
            task_id=task_id,
            trace_id=trace_id,
            event_type="task_queued",
            component="executor",
            status="queued",
            summary="Task was queued for execution.",
        )

        self.tasks[task_id] = task

        handle = asyncio.create_task(
            self._run_task(task, request),
        )

        self.handles[task_id] = handle

        return task

    async def _run_task(
        self,
        task: InProcessTask,
        request: TaskRequest,
    ) -> None:
        task.status = "running"
        await self._emit(
            task_id=task.task_id,
            trace_id=task.trace_id,
            event_type="task_started",
            component="executor",
            status="running",
            summary="Task execution started.",
        )

        initial_state = {
            "task_id": task.task_id,
            "trace_id": task.trace_id,
            "user_id": request.user_id,
            "original_task": request.task,
            "request_context": request.context,
            "completed_subtask_ids": set(),
            "specialist_results": {},
            "review_results": {},
            "review_history": [],
            "review_attempt": 0,
            "errors": [],
            "human_review_requested": request.human_review_requested,
        }

        try:
            config = {
                "configurable": {
                    "thread_id": task.task_id,
                }
            }
            result = await self.graph.ainvoke(initial_state, config=config) # type: ignore
            await self._handle_graph_result(task, result)

            if task.status == "waiting_approval":
                return
            task.final_answer = result.get("final_answer")

            errors = result.get("errors", [])

            if errors:
                task.error = errors[-1]

            await self._emit(
                task_id=task.task_id,
                trace_id=task.trace_id,
                event_type=(
                    "task_escalated"
                    if task.status == "escalated"
                    else "task_completed"
                ),
                component="executor",
                status=task.status,
                summary=f"Task finished with status '{task.status}'.",
            )

        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            await self._emit(
                task_id=task.task_id,
                trace_id=task.trace_id,
                event_type="task_failed",
                component="executor",
                status="failed",
                summary="Task execution failed.",
                metadata={
                    "error": str(exc),
                },
            )

    async def get(self, task_id: str) -> InProcessTask | None:
        return self.tasks.get(task_id)

    async def wait(self, task_id: str) -> InProcessTask:
        handle = self.handles.get(task_id)

        if handle is not None:
            await handle

        task = self.tasks.get(task_id)

        if task is None:
            raise KeyError(f"Task '{task_id}' was not found.")

        return task

    async def _handle_graph_result(
        self,
        task: InProcessTask,
        result: dict,
        ) -> None:
        interrupts = result.get("__interrupt__")

        if interrupts:
            interrupt_payload = interrupts[0].value

            task.status = "waiting_approval"
            task.pending_approval = interrupt_payload

            await self._emit(
                task_id=task.task_id,
                trace_id=task.trace_id,
                event_type="approval_requested",
                component="approval",
                status="waiting",
                summary="Task is waiting for human approval.",
                metadata={
                    "approval_id": interrupt_payload["approval_id"],
                },
            )

            return

        if result.get("escalated", False):
            task.status = "escalated"
        else:
            task.status = "completed"

        task.final_answer = result.get("final_answer")
        task.pending_approval = None

        errors = result.get("errors", [])

        if errors:
            task.error = errors[-1]

    async def resume(
        self,
        task_id: str,
        decision: ApprovalDecision,
    ) -> InProcessTask:
        task = self.tasks.get(task_id)

        if task is None:
            raise KeyError(f"Task '{task_id}' was not found.")

        if task.status != "waiting_approval":
            raise ValueError(
                f"Task '{task_id}' is not waiting for approval."
            )

        task.status = "running"
        task.pending_approval = None

        handle = asyncio.create_task(
            self._resume_task(task, decision),
        )

        self.handles[task_id] = handle

        return task

    async def _resume_task(
        self,
        task: InProcessTask,
        decision: ApprovalDecision,
    ) -> None:
        config: RunnableConfig = {
            "configurable": {
                "thread_id": task.task_id,
            }
        }

        try:
            result = await self.graph.ainvoke(
                Command(
                    resume=decision.model_dump(
                        mode="json",
                    ),
                ),
                config=config,
            )

            await self._handle_graph_result(task, result)

            if task.status == "completed":
                await self._emit(
                    task_id=task.task_id,
                    trace_id=task.trace_id,
                    event_type="task_completed",
                    component="executor",
                    status="completed",
                    summary="Task completed after human approval.",
                )

        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)



























            