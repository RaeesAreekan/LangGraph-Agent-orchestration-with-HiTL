from app.config import Settings
from app.memory.base import MemoryService
from app.memory.chroma import ChromaMemoryService
from app.memory.fake import FakeMemoryService


def create_memory_service(
    settings: Settings,
) -> MemoryService | None:
    if not settings.memory_enabled:
        return None

    if settings.memory_backend == "fake":
        return FakeMemoryService()

    if settings.openai_api_key is None:
        raise ValueError(
            "OPENAI_API_KEY is required when using Chroma memory."
        )

    return ChromaMemoryService(
        chroma_url=settings.chroma_url,
        collection_name=settings.chroma_collection,
        openai_api_key=settings.openai_api_key,
        embedding_model=settings.embedding_model,
    )