from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import EventRecord, TaskRecord
from app.schemas.domain import ExecutionEvent

from sqlalchemy.exc import IntegrityError
class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        task_id: str,
        trace_id: str,
        user_id: str,
        original_task: str,
        request_context: dict,
        human_review_requested: bool,
        status: str,
        idempotency_key: str | None = None,
        conversation_id: str | None = None,
    ) -> None:
        record = TaskRecord(
            task_id=task_id,
            trace_id=trace_id,
            user_id=user_id,
            original_task=original_task,
            request_context=request_context,
            human_review_requested=human_review_requested,
            status=status,
            idempotency_key=idempotency_key,
            conversation_id=conversation_id,
        )

        self.session.add(record)
        await self.session.commit()

    async def update(
        self,
        task_id: str,
        *,
        status: str,
        final_answer: dict | None = None,
        error: str | None = None,
        pending_approval: dict | None = None,
    ) -> None:
        record = await self.session.get(TaskRecord, task_id)

        if record is None:
            raise KeyError(f"Task '{task_id}' was not found.")

        record.status = status
        record.final_answer = final_answer
        record.error = error
        record.pending_approval = pending_approval

        await self.session.commit()

    async def get(self, task_id: str) -> TaskRecord | None:
        return await self.session.get(TaskRecord, task_id)

    async def get_by_idempotency_key(
        self,
        user_id: str,
        idempotency_key: str,
    ) -> TaskRecord | None:
        result = await self.session.execute(
            select(TaskRecord).where(
                TaskRecord.user_id == user_id,
                TaskRecord.idempotency_key == idempotency_key,
            )
        )

        return result.scalar_one_or_none()


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, event: ExecutionEvent) -> None:
        record = EventRecord(
            id=event.id,
            task_id=event.task_id,
            trace_id=event.trace_id,
            event_type=event.event_type,
            component=event.component,
            status=event.status,
            summary=event.summary,
            timestamp=event.timestamp,
            parent_event_id=event.parent_event_id,
            event_metadata=event.metadata,
        )

        self.session.add(record)
        await self.session.commit()

    async def list_for_task(
        self,
        task_id: str,
    ) -> list[ExecutionEvent]:
        result = await self.session.execute(
            select(EventRecord)
            .where(EventRecord.task_id == task_id)
            .order_by(EventRecord.timestamp),
        )

        records = result.scalars().all()

        return [
            ExecutionEvent(
                id=record.id,
                task_id=record.task_id,
                trace_id=record.trace_id,
                event_type=record.event_type,
                component=record.component,
                status=record.status,
                summary=record.summary,
                timestamp=record.timestamp,
                parent_event_id=record.parent_event_id,
                metadata=record.event_metadata,
            )
            for record in records
        ]