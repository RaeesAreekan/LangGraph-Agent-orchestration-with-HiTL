import pytest

from app.schemas.tools import DemoSearchInput, DemoSearchOutput
from app.tools.base import ToolContext
from app.tools.mcp_provider import McpToolProvider


class FakeMcpTool:
    name = "search"

    async def ainvoke(self, input_data: dict):
        return [
            {
                "title": "LangGraph documentation",
                "url": "https://example.com/langgraph",
                "snippet": "Graph-based agent workflows.",
            }
        ]


class FakeMcpClient:
    async def get_tools(self):
        return [FakeMcpTool()]


@pytest.mark.asyncio
async def test_mcp_provider_invokes_tool():
    provider = McpToolProvider(
        client=FakeMcpClient(),
    )

    result = await provider.invoke(
        tool_name="search",
        input_data={
            "query": "LangGraph",
            "limit": 1,
        },
        output_type=DemoSearchOutput,
        context=ToolContext(
            task_id="task-1",
            trace_id="trace-1",
            agent_name="researcher",
        ),
    )

    assert isinstance(result, DemoSearchOutput)
    assert result.results[0]["title"] == "LangGraph documentation"