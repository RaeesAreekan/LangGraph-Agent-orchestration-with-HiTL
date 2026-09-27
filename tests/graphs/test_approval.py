import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.builder import build_graph
from app.schemas.domain import ApprovalDecision


@pytest.mark.asyncio
async def test_workflow_pauses_and_resumes_for_human_approval():
    graph = build_graph(checkpointer=InMemorySaver())

    initial_state = {
        "task_id": "task-approval",
        "trace_id": "trace-approval",
        "user_id": "demo-user",
        "original_task": "Prepare a research brief",
        "request_context": {},
        "human_review_requested": True,
        "completed_subtask_ids": set(),
        "specialist_results": {},
        "review_results": {},
        "review_history": [],
        "review_attempt": 0,
        "errors": [],
    }

    config = {
        "configurable": {
            "thread_id": "task-approval",
        }
    }

    paused = await graph.ainvoke(
        initial_state, # type: ignore
        config=config, # type: ignore
    )

    assert "__interrupt__" in paused

    decision = ApprovalDecision(
        approval_id="approval-task-approval",
        decision="approve",
        reviewer_id="demo-reviewer",
        modification=None,
        comment="Approved for synthesis.",
    )

    resumed = await graph.ainvoke(
        Command(
            resume=decision.model_dump(mode="json"),
        ),
        config=config, # type: ignore
    )

    assert resumed["approval_decision"].decision == "approve"
    assert resumed["final_answer"] is not None