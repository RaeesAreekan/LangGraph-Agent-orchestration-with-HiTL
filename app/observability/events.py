"""
This can be replaced by Langsmith's event system once it is available.For now , a simple system is made
"""
from typing import Protocol

from app.schemas.domain import ExecutionEvent


class EventSink(Protocol):
    def append(self, event: ExecutionEvent) -> None:
        ...

    def list_for_task(self, task_id: str) -> list[ExecutionEvent]:
        ...


class InMemoryEventSink:
    def __init__(self) -> None:
        self.events: list[ExecutionEvent] = []

    def append(self, event: ExecutionEvent) -> None:
        self.events.append(event)

    def list_for_task(
        self,
        task_id: str,
    ) -> list[ExecutionEvent]:
        return [
            event
            for event in self.events
            if event.task_id == task_id
        ]