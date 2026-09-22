import pytest

from app.graph.builder import build_graph


@pytest.mark.asyncio
async def test_workflow_runs_specialists_and_synthesizes():
    graph = build_graph()

    initial_state = {
        "task_id": "task-1",
        "trace_id": "trace-1",
        "user_id": "demo-user",
        "original_task": "Prepare a research brief",
        "request_context": {},
        "completed_subtask_ids": set(),
        "specialist_results": {},
        "review_results": {},
        "errors": [],
    }

    result = await graph.ainvoke(initial_state) # type: ignore

    assert result["plan"] is not None
    assert result["completed_subtask_ids"] == {
        "research",
        "analysis",
    }
    assert set(result["specialist_results"]) == {
        "research",
        "analysis",
    }
    assert result["review_results"]["workflow"].decision == "approved"
    assert result["final_answer"] is not None