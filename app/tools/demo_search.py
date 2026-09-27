from pydantic import BaseModel, Field

from app.schemas.tools import ToolSpec
from app.tools.base import ToolContext

class DemoSearchInput(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=3, ge=1, le=10)


class DemoSearchOutput(BaseModel):
    results: list[dict[str, str]]


class DemoSearchTool:
    spec = ToolSpec(
        name="demo_search",
        description="Returns deterministic search results for testing.",
        input_schema=DemoSearchInput,
        output_schema=DemoSearchOutput,
        allowed_agents={"researcher"},
        requires_approval=False,
        timeout_seconds=5,
    )

    async def invoke(
        self,
        input_data: DemoSearchInput,
        context: ToolContext,
    ) -> DemoSearchOutput:
        results = [
            {
                "title": "LangGraph documentation",
                "url": "https://example.com/langgraph",
                "snippet": "A graph-based framework for stateful workflows.",
            },
            {
                "title": "Agent orchestration patterns",
                "url": "https://example.com/orchestration",
                "snippet": "Patterns for coordinating multiple specialist agents.",
            },
            {
                "title": "Typed tool interfaces",
                "url": "https://example.com/tools",
                "snippet": "Typed boundaries make tool calls easier to validate.",
            },
        ]

        return DemoSearchOutput(
            results=results[: input_data.limit],
        )