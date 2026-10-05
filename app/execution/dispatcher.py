from typing import Protocol

from app.schemas.api import TaskRequest
from app.schemas.domain import ApprovalDecision

class TaskDispatcher(Protocol):
    async def enqueue(
        self,
        task_id: str,
        request: TaskRequest,
    ) -> None:
        ...
    async def enqueue_resume(
        self,
        task_id: str,
        decision: ApprovalDecision,
    ) -> None:
        ...


class CeleryTaskDispatcher:
    async def enqueue(
        self,
        task_id: str,
        request: TaskRequest,
    ) -> None:

        # Enqueue the task for execution using Celery
        # Added inside the enqueue method to avoid circular import issues
        from app.execution.celery_tasks import run_workflow

        run_workflow.delay(
            task_id,
            request.model_dump(mode="json"),
        )

    async def enqueue_resume(
        self,
        task_id: str,
        decision: ApprovalDecision,
    ) -> None:
        # To prevent circular import issues, import the Celery task inside the method   
        from app.execution.celery_tasks import resume_workflow

        resume_workflow.delay(
            task_id,
            decision.model_dump(mode="json"),
        )