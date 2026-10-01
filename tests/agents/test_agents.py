import pytest

from app.agents.analyst import AnalystAgent
from app.agents.fake import fake_plan
from app.agents.model import FakeStructuredModel
from app.agents.researcher import ResearcherAgent
from app.agents.supervisor import SupervisorAgent
from app.schemas.domain import ExecutionPlan, SpecialistResult


@pytest.mark.asyncio
async def test_supervisor_returns_execution_plan():
    model = FakeStructuredModel()
    expected = fake_plan()
    model.enqueue(expected)

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


@pytest.mark.asyncio
async def test_researcher_returns_structured_result():
    model = FakeStructuredModel()

    model.enqueue(
        SpecialistResult(
            subtask_id="placeholder",
            status="success",
            answer="Research result",
            evidence=[],
            assumptions=[],
            confidence=0.9,
            tool_call_ids=[],
            attempt=99,
        )
    )

    researcher = ResearcherAgent(model)

    result = await researcher.run(
        original_task="Research LangGraph",
        search_results=[],
        attempt=2,
        feedback=[],
        tool_call_ids=["tool-call-1"],
    )

    assert result.subtask_id == "research"
    assert result.attempt == 2
    assert result.tool_call_ids == ["tool-call-1"]


@pytest.mark.asyncio
async def test_analyst_returns_structured_result():
    model = FakeStructuredModel()

    model.enqueue(
        SpecialistResult(
            subtask_id="placeholder",
            status="success",
            answer="Analysis result",
            evidence=[],
            assumptions=[],
            confidence=0.85,
            tool_call_ids=[],
            attempt=99,
        )
    )

    analyst = AnalystAgent(model)

    result = await analyst.run(
        original_task="Analyze the research problem",
        request_context={
            "budget": 1000,
        },
        attempt=1,
        feedback=[],
    )

    assert result.subtask_id == "analysis"
    assert result.attempt == 1
    assert result.tool_call_ids == []