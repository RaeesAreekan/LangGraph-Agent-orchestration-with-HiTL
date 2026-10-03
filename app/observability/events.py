"""
This can be replaced by Langsmith's event system once it is available.For now , a simple system is made
"""
from typing import Protocol

from app.schemas.domain import ExecutionEvent
from app.persistence.database import Database
from app.persistence.repositories import EventRepository

class EventSink(Protocol):
    async def append(self, event: ExecutionEvent) -> None:
        ...

    async def list_for_task(self, task_id: str) -> list[ExecutionEvent]:
        ...


class InMemoryEventSink:
    def __init__(self) -> None:
        self.events: list[ExecutionEvent] = []

    async def append(self, event: ExecutionEvent) -> None:
        self.events.append(event)

    async def list_for_task(
        self,
        task_id: str,
    ) -> list[ExecutionEvent]:
        return [
            event
            for event in self.events
            if event.task_id == task_id
        ]


class PersistentEventSink:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def append(self, event: ExecutionEvent) -> None:
        async with self.database.session() as session:
            repository = EventRepository(session)
            await repository.append(event)

    async def list_for_task(
        self,
        task_id: str,
    ) -> list[ExecutionEvent]:
        async with self.database.session() as session:
            repository = EventRepository(session)
            return await repository.list_for_task(task_id)