from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    allowed_agents: set[str] = Field(default_factory=set)
    requires_approval: bool = False
    timeout_seconds: int = Field(default=10, gt=0)


class ToolCallRecord(BaseModel):
    id: str
    tool_name: str
    agent_name: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    status: Literal["started", "succeeded", "failed"]
    latency_ms: int | None = None
    error: str | None = None