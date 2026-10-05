from dataclasses import dataclass
from typing import Protocol


@dataclass
class MemoryItem:
    id: str
    document: str
    metadata: dict
    distance: float | None = None


class MemoryService(Protocol):
    async def retrieve(
        self,
        *,
        user_id: str,
        conversation_id: str,
        query: str,
        limit: int,
    ) -> list[MemoryItem]:
        ...

    async def store(
        self,
        *,
        memory_id: str,
        user_id: str,
        conversation_id: str,
        document: str,
        metadata: dict,
    ) -> None:
        ...

    async def delete_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str,
    ) -> None:
        ...

    async def list_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str,
    ) -> list[MemoryItem]:
        ...