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


ReviewFunction = Callable[
    [dict[str, SpecialistResult], int],
    ReviewResult,
]

MAX_SPECIALIST_ATTEMPTS = 2

def planning_node(state: OrchestratorState) -> dict:
    return {
        "plan": fake_plan(),
    }


def research_node(state: OrchestratorState) -> dict:
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

    result = fake_research(
        attempt=attempt,
        feedback=feedback,
    )
    return {
        "specialist_results": {
            result.subtask_id: result,
        },
        "completed_subtask_ids": {result.subtask_id},
    }


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
        return "synthesis"

    return "end"