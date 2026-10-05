# Open source free alternative to OpenAI's embedding service using ChromaDB for memory storage and retrieval.
import asyncio

import chromadb
from chromadb.utils.embedding_functions import (
    OpenAIEmbeddingFunction,
)

from app.memory.base import MemoryItem

from urllib.parse import urlparse

class ChromaMemoryService:
    def __init__(
        self,
        *,
        chroma_url: str,
        collection_name: str,
        openai_api_key: str,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        parsed_url = urlparse(chroma_url)

        host = parsed_url.hostname or "localhost"
        port = parsed_url.port or 8000

        self.client = chromadb.HttpClient(
            host=host,
            port=port,
        )

        embedding_function = OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name=embedding_model,
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function, # type: ignore
        )
    
    async def retrieve(
        self,
        *,
        user_id: str,
        conversation_id: str,
        query: str,
        limit: int,
    ) -> list[MemoryItem]:
        result = await asyncio.to_thread(
            self.collection.query,
            query_texts=[query],
            n_results=limit,
            where={
                "user_id": user_id,
                "conversation_id": conversation_id,
            },
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0] # type: ignore
        metadatas = result.get("metadatas", [[]])[0] # type: ignore
        distances = result.get("distances", [[]])[0] # type: ignore

        return [
            MemoryItem(
                id=memory_id,
                document=document,
                metadata=metadata or {}, # type: ignore
                distance=distance,
            )
            for memory_id, document, metadata, distance in zip(
                ids,
                documents,
                metadatas,
                distances,
            )
        ]

    async def store(
        self,
        *,
        memory_id: str,
        user_id: str,
        conversation_id: str,
        document: str,
        metadata: dict,
    ) -> None:
        await asyncio.to_thread(
            self.collection.upsert,
            ids=[memory_id],
            documents=[document],
            metadatas=[
                {
                    **metadata,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                }
            ],
        )

    async def delete_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str,
    ) -> None:
        await asyncio.to_thread(
            self.collection.delete,
            where={
                "user_id": user_id,
                "conversation_id": conversation_id,
            },
        )

    async def list_conversation(
        self,
        *,
        user_id: str,
        conversation_id: str,
    ) -> list[MemoryItem]:
        result = await asyncio.to_thread(
            self.collection.get,
            where={
                "user_id": user_id,
                "conversation_id": conversation_id,
            },
        )

        return [
            MemoryItem(
                id=memory_id,
                document=document,
                metadata=metadata or {},
            )
            for memory_id, document, metadata in zip(
                result.get("ids", []),
                result.get("documents", []), # type: ignore
                result.get("metadatas", []), # type: ignore
            )
        ]