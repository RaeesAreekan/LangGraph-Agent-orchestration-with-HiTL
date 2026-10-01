import pytest

from app.agents.model import FakeStructuredModel
from app.agents.researcher import ResearcherAgent
from app.schemas.domain import SpecialistResult


@pytest.mark.asyncio
async def test_researcher_returns_structured_result():
    model = FakeStructuredModel()

    model.enqueue(
        SpecialistResult(
            subtask_id="placeholder",
            status="success",
            answer="The model found useful evidence.",
            evidence=[
                {
                    "source": "demo-source",
                    "detail": "Useful information.",
                }
            ],
            assumptions=[],
            confidence=0.9,
            tool_call_ids=[],
            attempt=99,
        )
    )

    researcher = ResearcherAgent(model)

    result = await researcher.run(
        original_task="Research LangGraph",
        search_results=[
            {
                "source": "demo-source",
                "detail": "Useful information.",
            }
        ],
        attempt=2,
        feedback=["Improve evidence quality."],
        tool_call_ids=["tool-call-1"],
    )

    assert isinstance(result, SpecialistResult)
    assert result.subtask_id == "research"
    assert result.attempt == 2
    assert result.tool_call_ids == ["tool-call-1"]