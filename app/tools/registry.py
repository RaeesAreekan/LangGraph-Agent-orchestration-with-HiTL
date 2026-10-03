import asyncio
import time
from uuid import uuid4

from app.schemas.tools import ToolCallRecord
from app.tools.base import Tool, ToolContext, ToolInvocation
from app.observability.events import EventSink
from app.schemas.domain import ExecutionEvent

class ToolRegistry:
    def __init__(self, event_sink: EventSink | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self.records: list[ToolCallRecord] = []
        self.event_sink: EventSink | None = event_sink

    def register(self, tool: Tool) -> None:
        tool_name = tool.spec.name

        if tool_name in self._tools:
            raise ValueError(
                f"Tool '{tool_name}' is already registered."
            )

        self._tools[tool_name] = tool

    def get_tool(self, tool_name: str) -> Tool:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise KeyError(
                f"Tool '{tool_name}' is not registered."
            ) from exc

    def tools_for_agent(self, agent_name: str) -> list[str]:
        return [
            tool.spec.name
            for tool in self._tools.values()
            if agent_name in tool.spec.allowed_agents
        ]
    async def _emit_event(
        self,
        event: ExecutionEvent,
    ) -> None:
        if self.event_sink is not None:
            await self.event_sink.append(event)

    async def invoke(
        self,
        tool_name: str,
        agent_name: str,
        input_data: dict,
        context: ToolContext,
    ) -> ToolInvocation:
        tool = self.get_tool(tool_name)
        spec = tool.spec
        started_at = time.perf_counter()

        record = ToolCallRecord(
            id=str(uuid4()),
            tool_name=tool_name,
            agent_name=agent_name,
            input=input_data,
            status="started",
        )

        self.records.append(record)
        await self._emit_event(
            ExecutionEvent(
                task_id=context.task_id,
                trace_id=context.trace_id,
                event_type="tool_started",
                component=f"tool:{tool_name}",
                status="started",
                summary=f"Tool '{tool_name}' started.",
                metadata={
                    "tool_call_id": record.id,
                    "agent_name": agent_name,
                },
            )
        )

        try:
            if agent_name not in spec.allowed_agents:
                raise PermissionError(
                    f"Agent '{agent_name}' is not allowed to use "
                    f"tool '{tool_name}'."
                )

            if spec.requires_approval:
                raise PermissionError(
                    f"Tool '{tool_name}' requires approval."
                )

            validated_input = spec.input_schema.model_validate(
                input_data,
            )

            raw_output = await asyncio.wait_for(
                tool.invoke(
                    validated_input,
                    context,
                ),
                timeout=spec.timeout_seconds,
            )

            validated_output = spec.output_schema.model_validate(
                raw_output,
            )

            record.status = "succeeded"
            record.output = validated_output.model_dump(
                mode="json",
            )
            await self._emit_event(
                ExecutionEvent(
                    task_id=context.task_id,
                    trace_id=context.trace_id,
                    event_type="tool_completed",
                    component=f"tool:{tool_name}",
                    status="succeeded",
                    summary=f"Tool '{tool_name}' completed.",
                    metadata={
                        "tool_call_id": record.id,
                        "latency_ms": record.latency_ms,
                    },
                )
            )

            return ToolInvocation(
                output=validated_output,
                record=record,
            )

        except Exception as exc:
            record.status = "failed"
            record.error = str(exc)
            await self._emit_event(
                ExecutionEvent(
                    task_id=context.task_id,
                    trace_id=context.trace_id,
                    event_type="tool_failed",
                    component=f"tool:{tool_name}",
                    status="failed",
                    summary=f"Tool '{tool_name}' failed.",
                    metadata={
                        "tool_call_id": record.id,
                        "error": str(exc),
                    },
                )
            )
            raise

        finally:
            record.latency_ms = int(
                (time.perf_counter() - started_at) * 1000,
            )