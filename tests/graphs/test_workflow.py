from unittest import result

import pytest

from app.graph.builder import build_graph
from app.schemas.domain import ReviewResult


def always_reject_review(results, attempt: int) -> ReviewResult:
    return ReviewResult(
        subtask_id="workflow",
        target_subtask_id="research",
        decision="needs_revision",
        quality_score=0.4,
        feedback=["Evidence is still insufficient."],
        missing_evidence=["More supporting evidence."],
    )
@pytest.mark.asyncio
async def test_second_rejection_escalates_instead_of_looping():
    graph = build_graph(review_fn=always_reject_review)

    result = await graph.ainvoke(make_initial_state()) # type: ignore

    assert result["escalated"] is True
    assert result.get("final_answer") is None
    assert result["specialist_results"]["research"].attempt == 2
    assert len(result["review_history"]) == 2
    assert result["review_history"][0].target_subtask_id == "research"


def make_initial_state():
    return {
        "task_id": "task-1",
        "trace_id": "trace-1",
        "user_id": "demo-user",
        "original_task": "Prepare a research brief",
        "request_context": {},
        "completed_subtask_ids": set(),
        "specialist_results": {},
        "review_results": {},
        "review_history": [],
        "review_attempt": 0,
        "errors": [],
    }

@pytest.mark.asyncio
async def test_workflow_revises_rejected_specialist_result():
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
        "review_history": [],
        "review_attempt": 0,
        "errors": [],
    }

    result = await graph.ainvoke(initial_state) # type: ignore

    assert result["final_answer"] is not None

    # Both specialists completed.
    assert result["completed_subtask_ids"] == {
        "research",
        "analysis",
    }

    # Research was rejected once and then revised.
    assert result["specialist_results"]["research"].attempt == 2

    # Analysis was not revised.
    assert result["specialist_results"]["analysis"].attempt == 1

    # The reviewer ran twice.
    assert result["review_attempt"] == 2
    assert [
        review.decision
        for review in result["review_history"]
    ] == [
        "needs_revision",
        "approved",
    ]