import pytest

from app.execution.in_process import InProcessExecutor
from app.memory.fake import FakeMemoryService
from app.observability.events import InMemoryEventSink
from app.schemas.api import TaskRequest


class CapturingGraph:
    def __init__(self):
        self.initial_state = None

    async def ainvoke(self, state, config):
        self.initial_state = state

        return {
            "final_answer": None,
            "errors": [],
        }


@pytest.mark.asyncio
async def test_memories_are_retrieved_before_workflow():
    memory = FakeMemoryService()

    await memory.store(
        memory_id="memory-1",
        user_id="demo-user",
        conversation_id="conversation-1",
        document="The user prefers concise technical answers.",
        metadata={"memory_type": "preference"},
    )

    graph = CapturingGraph()

    executor = InProcessExecutor(
        graph=graph,
        event_sink=InMemoryEventSink(),
        memory_service=memory,
        memory_top_k=5,
    )

    request = TaskRequest(
        user_id="demo-user",
        task="Prepare a technical answer",
        conversation_id="conversation-1",
    )

    task = await executor.submit(request)
    await executor.wait(task.task_id)

    assert graph.initial_state is not None
    assert graph.initial_state["memories"] == [
        "The user prefers concise technical answers."
    ]