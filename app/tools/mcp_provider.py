from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel

from app.tools.base import ToolContext

from app.schemas.tools import (
    DemoSearchInput,
    DemoSearchOutput,
)
from app.schemas.tools import ToolSpec
from app.tools.base import Tool

# This is a MCP client that can be used to invoke tools on multiple servers. It is used by the MCP tool provider to invoke tools on the MCP servers.
class McpToolProvider:
    def __init__(
        self,
        client: Any,
    ) -> None:
        self.client = client
        self._tools: dict[str, Any] = {}

    @classmethod
    def from_connections(
        cls,
        connections: dict,
    ) -> "McpToolProvider":
        client = MultiServerMCPClient(
            connections,
        )

        return cls(client)

    async def initialize(self) -> None:
        tools = await self.client.get_tools()

        self._tools = {
            tool.name: tool
            for tool in tools
        }

    async def invoke(
        self,
        tool_name: str,
        input_data: dict,
        output_type: type[BaseModel],
        context: ToolContext,
    ) -> BaseModel:
        if not self._tools:
            await self.initialize()

        tool = self._tools.get(tool_name)

        if tool is None:
            raise KeyError(
                f"MCP tool '{tool_name}' was not found."
            )

        raw_output = await tool.ainvoke(input_data)

        # Our demo search server returns a list of results.
        # Convert that into the application's typed output model.
        if isinstance(raw_output, dict):
            if "web" in raw_output:
                raw_output = {
                    "results": raw_output["web"].get("results", [])
                }
            elif "results" not in raw_output:
                raw_output = {"results": []}

        elif isinstance(raw_output, list):
            raw_output = {
                "results": raw_output,
            }

        return output_type.model_validate(
            raw_output,
        )

class McpSearchTool:
    spec = ToolSpec(
        name="mcp_search",
        description="Searches through an MCP server.",
        input_schema=DemoSearchInput,
        output_schema=DemoSearchOutput,
        allowed_agents={"researcher"},
        requires_approval=False,
        timeout_seconds=15,
    )

    def __init__(
        self,
        provider: McpToolProvider,
    ) -> None:
        self.provider = provider

    async def invoke(
        self,
        input_data: DemoSearchInput,
        context: ToolContext,
    ) -> DemoSearchOutput:
        result = await self.provider.invoke(
            tool_name="brave_web_search",
            input_data={
                "query": input_data.query,
                "count": input_data.limit,
                "safesearch": "moderate",
                "search_lang": "en",
            },
            output_type=DemoSearchOutput,
            context=context,
        )

        return DemoSearchOutput.model_validate(result)