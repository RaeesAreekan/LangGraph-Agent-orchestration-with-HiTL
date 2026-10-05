import asyncio
from dataclasses import dataclass
from unittest import result
from uuid import uuid4

from langgraph.func import task

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

from app.persistence.database import Database
from app.persistence.repositories import TaskRepository
from app.execution.dispatcher import TaskDispatcher

from sqlalchemy.exc import IntegrityError
@dataclass
class InProcessTask:
    task_id: str
    trace_id: str
    status: str
    final_answer: FinalAnswer | None = None
    error: str | None = None
    pending_approval: dict | None = None

    user_id: str | None = None
    original_task: str | None = None
    conversation_id: str | None = None


class InProcessExecutor:
    def __init__(self, graph=None,event_sink: EventSink | None = None,database: Database | None = None,dispatcher: TaskDispatcher | None = None,memory_service=None,memory_top_k: int = 5) -> None:
        self.event_sink = event_sink or InMemoryEventSink()
        self.graph = graph or build_graph(event_sink=self.event_sink)
        self.tasks: dict[str, InProcessTask] = {}
        self.handles: dict[str, asyncio.Task] = {}
        self.database = database
        self.dispatcher = dispatcher
        self.memory_service = memory_service
        self.memory_top_k = memory_top_k

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
        if (
            self.database is not None
            and request.idempotency_key is not None
        ):
            existing = await self._get_by_idempotency_key(request)

            if existing is not None:
                task = self._task_from_record(existing)
                self.tasks[task.task_id] = task
                return task
        task_id = str(uuid4())
        trace_id = str(uuid4())

        task = InProcessTask(
            task_id=task_id,
            trace_id=trace_id,
            status="queued",
            user_id=request.user_id,
            original_task=request.task,
            conversation_id=request.conversation_id,
        )

        self.tasks[task_id] = task
        try:
            await self._persist_new_task(task, request)
        except IntegrityError:
            if request.idempotency_key is None:
                raise

            existing = await self._get_by_idempotency_key(request)

            if existing is None:
                raise

            task = self._task_from_record(existing)
            self.tasks[task.task_id] = task
            return task
        await self._emit(
            task_id=task_id,
            trace_id=trace_id,
            event_type="task_queued",
            component="executor",
            status="queued",
            summary="Task was queued for execution.",
        )
        if self.dispatcher is not None:
            await self.dispatcher.enqueue(
                task.task_id,
                request,
            )
        else:
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
        await self._persist_task(task)
        await self._emit(
            task_id=task.task_id,
            trace_id=task.trace_id,
            event_type="task_started",
            component="executor",
            status="running",
            summary="Task execution started.",
        )
        memory_documents, memory_ids = (
        await self._retrieve_memories(request)
        )

        request_context = {
            **request.context,
            "retrieved_memories": memory_documents,
        }

        initial_state = {
            "task_id": task.task_id,
            "trace_id": task.trace_id,
            "user_id": request.user_id,
            "original_task": request.task,
            "request_context": request.context,
            "memories": memory_documents,
            "memory_ids_used": memory_ids,
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

            if task.status == "completed":
                await self._store_task_memory(task)

            errors = result.get("errors", [])

            if errors:
                task.error = errors[-1]

            await self._persist_task(task)

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
            await self._persist_task(task)
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
        if self.database is None:
            return self.tasks.get(task_id)
        
        async with self.database.session() as session:
            repository = TaskRepository(session)
            record = await repository.get(task_id)

            if record is None:
                return self.tasks.get(task_id)

            return self._task_from_record(record)

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
            await self._persist_task(task)

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
        task = await self.get(task_id)

        if task is None:
            raise KeyError(f"Task '{task_id}' was not found.")

        if task.status != "waiting_approval":
            raise ValueError(
                f"Task '{task_id}' is not waiting for approval."
            )

        if (
            task.pending_approval is None
            or task.pending_approval.get("approval_id") != decision.approval_id
        ):
            raise ValueError(
                f"Approval '{decision.approval_id}' is not pending for task '{task_id}'."
            )

        self.tasks[task_id] = task
        if self.dispatcher is not None:
            original_pending_approval = task.pending_approval

            task.status = "running"
            task.pending_approval = None
            await self._persist_task(task)

            try:
                await self.dispatcher.enqueue_resume(
                    task_id,
                    decision,
                )
            except Exception:
                # Restore the approval state if queueing failed.
                task.status = "waiting_approval"
                task.pending_approval = original_pending_approval
                await self._persist_task(task)
                raise

            return task

        # In-process mode: preserve the existing behavior.
        task.status = "running"
        task.pending_approval = None
        await self._persist_task(task)

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
            await self._persist_task(task)

            if task.status == "completed":
                await self._store_task_memory(task)
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
            await self._persist_task(task)


    async def _persist_new_task(
        self,
        task: InProcessTask,
        request: TaskRequest,
    ) -> None:
        if self.database is None:
            return

        async with self.database.session() as session:
            repository = TaskRepository(session)

            await repository.create(
                task_id=task.task_id,
                trace_id=task.trace_id,
                user_id=request.user_id,
                original_task=request.task,
                request_context=request.context,
                human_review_requested=request.human_review_requested,
                status=task.status,
                idempotency_key=request.idempotency_key,
                conversation_id=request.conversation_id,
            )  

    async def _persist_task(
        self,
        task: InProcessTask,
    ) -> None:
        if self.database is None:
            return

        async with self.database.session() as session:
            repository = TaskRepository(session)

            await repository.update(
                task.task_id,
                status=task.status,
                final_answer=(
                    task.final_answer.model_dump(mode="json")
                    if task.final_answer is not None
                    else None
                ),
                error=task.error,
                pending_approval=task.pending_approval,
            )

    def _task_from_record(
        self,
        record,
    ) -> InProcessTask:
        return InProcessTask(
            task_id=record.task_id,
            trace_id=record.trace_id,
            status=record.status,
            final_answer=(
                FinalAnswer.model_validate(record.final_answer)
                if record.final_answer is not None
                else None
            ),
            error=record.error,
            pending_approval=record.pending_approval,
            user_id=getattr(record, "user_id", None),
            original_task=getattr(record, "original_task", None),
            conversation_id=getattr(record, "conversation_id", None),
        )

    async def run_existing_task(
        self,
        task: InProcessTask,
        request: TaskRequest,
    ) -> None:
        await self._run_task(
            task,
            request,
        )

    async def run_existing_resume(
        self,
        task: InProcessTask,
        decision: ApprovalDecision,
    ) -> None:
        self.tasks[task.task_id] = task

        await self._resume_task(
            task,
            decision,
        )

    async def _get_by_idempotency_key(
        self,
        request: TaskRequest,
        ):
        assert self.database is not None
        async with self.database.session() as session:
            repository = TaskRepository(session)

            return await repository.get_by_idempotency_key(
                request.user_id,
                request.idempotency_key,  # type: ignore[arg-type]
            )

    async def _retrieve_memories(
        self,
        request: TaskRequest,
    ) -> tuple[list[str], list[str]]:
        if (
            self.memory_service is None
            or request.conversation_id is None
        ):
            return [], []

        items = await self.memory_service.retrieve(
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            query=request.task,
            limit=self.memory_top_k,
        )

        return (
            [item.document for item in items],
            [item.id for item in items],
        )
    
    async def _store_task_memory(
        self,
        task: InProcessTask,
    ) -> None:
        if (
            self.memory_service is None
            or task.user_id is None
            or task.conversation_id is None
            or task.original_task is None
            or task.final_answer is None
        ):
            return

        final_answer = task.final_answer

        document = (
            f"Task:\n{task.original_task}\n\n"
            f"Final answer:\n{final_answer.title}\n"
            f"{final_answer.body}"
        )

        await self.memory_service.store(
            memory_id=f"task-summary:{task.task_id}",
            user_id=task.user_id,
            conversation_id=task.conversation_id,
            document=document,
            metadata={
                "memory_type": "task_summary",
                "task_id": task.task_id,
                "trace_id": task.trace_id,
            },
        )





















            