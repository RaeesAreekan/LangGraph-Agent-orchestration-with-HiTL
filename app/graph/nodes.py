from app.agents.fake import (
    fake_analysis,
    fake_plan,
    fake_research,
    fake_review,
    fake_synthesis,
)
from app.graph.state import OrchestratorState


def planning_node(state: OrchestratorState) -> dict:
    return {
        "plan": fake_plan(),
    }


def research_node(state: OrchestratorState) -> dict:
    result = fake_research()

    return {
        "specialist_results": {
            result.subtask_id: result,
        },
        "completed_subtask_ids": {result.subtask_id},
    }


def analysis_node(state: OrchestratorState) -> dict:
    result = fake_analysis()

    return {
        "specialist_results": {
            result.subtask_id: result,
        },
        "completed_subtask_ids": {result.subtask_id},
    }


def review_node(state: OrchestratorState) -> dict:
    review = fake_review(state["specialist_results"]) # type: ignore

    return {
        "review_results": {
            review.subtask_id: review,
        },
    }


def synthesis_node(state: OrchestratorState) -> dict:
    final_answer = fake_synthesis(
        state["specialist_results"], # type: ignore
    )

    return {
        "final_answer": final_answer,
    }