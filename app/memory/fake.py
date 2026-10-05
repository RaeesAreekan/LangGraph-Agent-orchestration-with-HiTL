from app.memory.base import MemoryItem


class FakeMemoryService:
    def __init__(self) -> None:
        self.items: dict[str, MemoryItem] = {}

    async def retrieve(
        self,
        *,
        user_id: str,
        conversation_id: str,
        query: str,
        limit: int,
    ) -> list[MemoryItem]:
        matching = [
            item
            for item in self.items.values()
            if item.metadata.get("user_id") == user_id
            and item.metadata.get("conversation_id")
            == conversation_id
        ]

        return matching[:limit]

    async def store(
        self,
        *,
        memory_id: str,
        user_id: str,
        conversation_id: str,
        document: str,
        metadata: dict,
    ) -> None:
        self.items[memory_id] = MemoryItem(
            id=memory_id,
            document=document,
            metadata={
                **metadata,
                "user_id": user_id,
                "conversation_id": conversation_id,
            },
        )

    async def delete_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str,
    ) -> None:
        self.items = {
            key: value
            for key, value in self.items.items()
            if not (
                value.metadata.get("user_id") == user_id
                and value.metadata.get("conversation_id")
                == conversation_id
            )
        }

    async def list_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str,
    ) -> list[MemoryItem]:
        return await self.retrieve(
            user_id=user_id,
            conversation_id=conversation_id,
            query="",
            limit=100,
        )