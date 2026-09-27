import pytest
from pydantic import BaseModel, ValidationError

from app.tools.base import ToolContext
from app.tools.demo_search import DemoSearchTool
from app.tools.registry import ToolRegistry
from app.graph.nodes import make_research_node

@pytest.mark.asyncio
async def test_allowed_agent_can_invoke_tool():
    registry = ToolRegistry()
    registry.register(DemoSearchTool()) # type: ignore

    invocation = await registry.invoke(
        tool_name="demo_search",
        agent_name="researcher",
        input_data={
            "query": "LangGraph",
            "limit": 2,
        },
        context=ToolContext(
            task_id="task-1",
            trace_id="trace-1",
            agent_name="researcher",
        ),
    )

    assert len(invocation.output.results) == 2 # type: ignore
    assert invocation.record.status == "succeeded"
    assert invocation.record.tool_name == "demo_search"


@pytest.mark.asyncio
async def test_disallowed_agent_cannot_invoke_tool():
    registry = ToolRegistry()
    registry.register(DemoSearchTool()) # type: ignore

    with pytest.raises(PermissionError):
        await registry.invoke(
            tool_name="demo_search",
            agent_name="analyst",
            input_data={
                "query": "LangGraph",
                "limit": 2,
            },
            context=ToolContext(
                task_id="task-1",
                trace_id="trace-1",
                agent_name="analyst",
            ),
        )

    assert registry.records[-1].status == "failed"


@pytest.mark.asyncio
async def test_invalid_tool_input_is_rejected():
    registry = ToolRegistry()
    registry.register(DemoSearchTool()) # type: ignore

    with pytest.raises(ValidationError):
        await registry.invoke(
            tool_name="demo_search",
            agent_name="researcher",
            input_data={
                "query": "",
                "limit": 2,
            },
            context=ToolContext(
                task_id="task-1",
                trace_id="trace-1",
                agent_name="researcher",
            ),
        )

    assert registry.records[-1].status == "failed"

@pytest.mark.asyncio
async def test_research_node_uses_tool_registry():
    registry = ToolRegistry()
    registry.register(DemoSearchTool()) # type: ignore

    research_node = make_research_node(registry)

    state = {
        "task_id": "task-1",
        "trace_id": "trace-1",
        "original_task": "Research LangGraph orchestration",
        "specialist_results": {},
        "review_results": {},
    }

    update = await research_node(state) # type: ignore

    result = update["specialist_results"]["research"]

    assert result.status == "success"
    assert result.tool_call_ids
    assert len(registry.records) == 1
    assert registry.records[0].tool_name == "demo_search"
    assert registry.records[0].status == "succeeded"