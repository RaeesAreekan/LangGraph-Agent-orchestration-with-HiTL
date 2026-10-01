import pytest

from app.agents.fake import fake_plan
from app.agents.model import FakeStructuredModel
from app.agents.supervisor import SupervisorAgent
from app.schemas.domain import ExecutionPlan


@pytest.mark.asyncio
async def test_supervisor_returns_structured_execution_plan():
    model = FakeStructuredModel()
    expected_plan = fake_plan()

    model.enqueue(expected_plan)

    supervisor = SupervisorAgent(model)

    result = await supervisor.run(
        original_task="Prepare a research brief",
        user_id="demo-user",
        request_context={},
        memories=[],
        specialist_names=["researcher", "analyst"],
    )

    assert isinstance(result, ExecutionPlan)
    assert result.subtasks
    assert {
        subtask.specialist
        for subtask in result.subtasks
    } == {
        "researcher",
        "analyst",
    }