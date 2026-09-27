from app.agents.fake import (
    fake_analysis,
    fake_plan,
    fake_research,
    fake_review,
    fake_synthesis,
)
from app.graph.state import OrchestratorState
from app.schemas.domain import SpecialistResult

from collections.abc import Callable

from app.schemas.domain import ReviewResult
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry

ReviewFunction = Callable[
    [dict[str, SpecialistResult], int],
    ReviewResult,
]

from uuid import uuid4

from langgraph.types import interrupt

from app.schemas.domain import ApprovalDecision

MAX_SPECIALIST_ATTEMPTS = 2

def planning_node(state: OrchestratorState) -> dict:
    return {
        "plan": fake_plan(),
    }

def make_research_node(tool_registry: ToolRegistry):
    async def research_node(state: OrchestratorState) -> dict:
        previous_result = state.get(
            "specialist_results",
            {},
        ).get("research")

        attempt = 1

        if previous_result is not None:
            attempt = previous_result.attempt + 1
        previous_review = state.get(
            "review_results",
            {},
        ).get("workflow")

        feedback = []

        if previous_review is not None:
            feedback = previous_review.feedback 

        ## Tool call before fake research agent call
        invocation = await tool_registry.invoke(
            tool_name="demo_search",
            agent_name="researcher",
            input_data={
                "query": state["original_task"], # type: ignore
                "limit": 3,
            },
            context=ToolContext(
                task_id=state["task_id"], # type: ignore
                trace_id=state["trace_id"], # type: ignore
                agent_name="researcher",
            ),
        )
        result = fake_research(
            search_results=invocation.output.results, # type: ignore
            attempt=attempt,
            feedback=feedback,
            tool_call_ids=[
                invocation.record.id,
            ],
        )
        return {
            "specialist_results": {
                result.subtask_id: result,
            },
            "completed_subtask_ids": {result.subtask_id},
        }

    return research_node

def analysis_node(state: OrchestratorState) -> dict:
    previous_result = state.get(
        "specialist_results",
        {},
    ).get("analysis")

    attempt = 1

    if previous_result is not None:
        attempt = previous_result.attempt + 1

    result = fake_analysis(attempt=attempt)

    return {
        "specialist_results": {
            result.subtask_id: result,
        },
        "completed_subtask_ids": {
            result.subtask_id,
        },
    }


def make_review_node(
    review_fn: ReviewFunction = fake_review,
):
    def review_node(state: OrchestratorState) -> dict:
        attempt = state.get("review_attempt", 0) + 1

        review = review_fn(
            state["specialist_results"], # type: ignore
            attempt,
        )

        update = {
            "review_results": {
                review.subtask_id: review,
            },
            "review_history": [review],
            "review_attempt": attempt,
        }

        if review.decision == "needs_revision":
            target_id = review.target_subtask_id
            results = state["specialist_results"] # type: ignore

            if (
                target_id is None
                or target_id not in results
                or results[target_id].attempt >= MAX_SPECIALIST_ATTEMPTS
            ):
                update["escalated"] = True
                update["errors"] = [
                    "Maximum specialist attempts exceeded.",
                ]

        return update

    return review_node


def synthesis_node(state: OrchestratorState) -> dict:
    final_answer = fake_synthesis(
        state["specialist_results"], # type: ignore
    )

    return {
        "final_answer": final_answer,
    }

def route_after_review(state: OrchestratorState) -> str:
    
    if state.get("escalated", False):
        return "end"

    review = state["review_results"]["workflow"] # type: ignore

    if review.decision == "needs_revision":
        return review.target_subtask_id or "end"

    if review.decision == "approved":
        if state.get("human_review_requested", False):
            return "approval"

        return "synthesis"

    return "end"

def approval_node(state: OrchestratorState) -> dict:
    approval_id = f"approval-{state['task_id']}" # type: ignore

    payload = {
        "approval_id": approval_id,
        "task_id": state["task_id"], # type: ignore
        "reason": "Human review was requested before synthesis.",
        "task": state["original_task"], # type: ignore
        "plan": state["plan"].model_dump(mode="json"), # type: ignore
        "specialist_results": {
            key: value.model_dump(mode="json")
            for key, value in state["specialist_results"].items() # type: ignore
        },
    }

    decision_data = interrupt(
        payload,
        response_schema=ApprovalDecision,
    )

    decision = ApprovalDecision.model_validate(
        decision_data,
    )

    return {
        "approval_decision": decision,
        "approval_rejected": decision.decision == "reject",
    }


def route_after_approval(
    state: OrchestratorState,
) -> str:
    decision = state["approval_decision"] # type: ignore

    assert decision is not None
    if decision.decision in {"approve", "modify"}:
        return "synthesis"

    return "end"