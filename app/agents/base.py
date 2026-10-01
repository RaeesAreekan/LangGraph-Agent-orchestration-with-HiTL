from typing import Protocol

from pydantic import BaseModel


class StructuredModel(Protocol):
    async def ainvoke(
        self,
        system_prompt: str,
        user_prompt: str,
        output_type: type[BaseModel],
    ) -> BaseModel:
        ...