import pytest

from app.agents.model import FakeStructuredModel
from app.schemas.domain import SpecialistResult


@pytest.mark.asyncio
async def test_fake_structured_model_returns_queued_output():
    model = FakeStructuredModel()

    expected = SpecialistResult(
        subtask_id="research",
        status="success",
        answer="Test answer",
        evidence=[],
        assumptions=[],
        confidence=0.9,
        tool_call_ids=[],
        attempt=1,
    )

    model.enqueue(expected)

    result = await model.ainvoke(
        system_prompt="You are a researcher.",
        user_prompt="Research LangGraph.",
        output_type=SpecialistResult,
    )

    assert result == expected