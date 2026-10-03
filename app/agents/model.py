from collections import deque
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.agents.base import StructuredModel
from app.config import Settings


class FakeStructuredModel:
    def __init__(self) -> None:
        self._outputs: deque[BaseModel] = deque()

    def enqueue(self, output: BaseModel) -> None:
        self._outputs.append(output)

    async def ainvoke(
        self,
        system_prompt: str,
        user_prompt: str,
        output_type: type[BaseModel],
    ) -> BaseModel:
        if not self._outputs:
            raise RuntimeError(
                "FakeStructuredModel has no queued output."
            )

        output = self._outputs.popleft()

        return output_type.model_validate(
            output,
        )


class OpenAIStructuredModel:
    def __init__(self, settings: Settings) -> None:
        self._model = ChatOpenAI(
            model=settings.specialist_model,
            api_key=settings.openai_api_key, # type: ignore
        )

    async def ainvoke(
        self,
        system_prompt: str,
        user_prompt: str,
        output_type: type[BaseModel],
    ) -> BaseModel:
        structured_model = self._model.with_structured_output(
            output_type,
            method = "function_calling"
        )

        result: Any = await structured_model.ainvoke(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )

        return output_type.model_validate(result)