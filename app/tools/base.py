from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from app.schemas.tools import ToolCallRecord, ToolSpec


class ToolContext(BaseModel):
    task_id: str
    trace_id: str
    agent_name: str


class Tool(Protocol):
    spec: ToolSpec

    async def invoke(
        self,
        input_data: BaseModel,
        context: ToolContext,
    ) -> BaseModel:
        ...


@dataclass
class ToolInvocation:
    output: BaseModel
    record: ToolCallRecord