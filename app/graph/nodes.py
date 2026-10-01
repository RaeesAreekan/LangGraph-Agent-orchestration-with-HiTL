from app.agents.fake import (
    fake_analysis,
    fake_plan,
    fake_research,
    fake_review,
    fake_synthesis,
)

from app.agents.analyst import AnalystAgent

from app.agents.researcher import ResearcherAgent
from app.agents.supervisor import SupervisorAgent

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

from app.agents.reviewer import ReviewerAgent

from app.agents.synthesizer import SynthesizerAgent

MAX_SPECIALIST_ATTEMPTS = 2

def make_planning_node(
    supervisor: SupervisorAgent | None = None,
):
    async def planning_node(
        state: OrchestratorState,
    ) -> dict:
        if supervisor is None:
            return {
                "plan": fake_plan(),
            }

        plan = await supervisor.run(
            original_task=state["original_task"], # type: ignore
            user_id=state["user_id"], # type: ignore
            request_context=state.get(
                "request_context",
                {},
            ),
            memories=state.get(
                "memories",
                [],
            ),
            specialist_names=[
                "researcher",
                "analyst",
            ],
        )

        return {
            "plan": plan,
        }

    return planning_node
def make_research_node(tool_registry: ToolRegistry,researcher:ResearcherAgent | None = None):
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
            tool_name="mcp_search",
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
        if researcher:
            result = await researcher.run(
                original_task=state["original_task"], # type: ignore
                search_results=invocation.output.results, # type: ignore
                attempt=attempt,
                feedback=feedback,
                tool_call_ids=[
                    invocation.record.id,
                ],
            )
        else:
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

def make_analysis_node(
    analyst: AnalystAgent | None = None,
):
    async def analysis_node(
        state: OrchestratorState,
    ) -> dict:
        previous_result = state.get(
            "specialist_results",
            {},
        ).get("analysis")

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

        if analyst is None:
            result = fake_analysis(
                attempt=attempt,
            )
        else:
            result = await analyst.run(
                original_task=state["original_task"], # type: ignore
                request_context=state.get(
                    "request_context",
                    {},
                ),
                attempt=attempt,
                feedback=feedback,
            )

        return {
            "specialist_results": {
                result.subtask_id: result,
            },
            "completed_subtask_ids": {
                result.subtask_id,
            },
        }

    return analysis_node

def make_review_node(
    reviewer: ReviewerAgent | None = None,
    review_fn: ReviewFunction = fake_review,
):
    async def review_node(state: OrchestratorState) -> dict:
        attempt = state.get("review_attempt", 0) + 1

        if reviewer is None:
            review = review_fn(
                state["specialist_results"], # type: ignore
                attempt,
            )
        else:
            review = await reviewer.run(
                original_task=state["original_task"], # type: ignore
                specialist_results=state["specialist_results"], # type: ignore
                attempt=attempt, # type: ignore
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


def make_synthesis_node(
    synthesizer: SynthesizerAgent | None = None,
):
    async def synthesis_node(
        state: OrchestratorState,
    ) -> dict:
        if synthesizer is None:
            final_answer = fake_synthesis(
                state["specialist_results"], # type: ignore
            )
        else:
            final_answer = await synthesizer.run(
                original_task=state["original_task"], # type: ignore
                plan=state["plan"], # type: ignore
                specialist_results=state["specialist_results"], # type: ignore
                review_results=state["review_results"], # type: ignore
            )

        return {
            "final_answer": final_answer,
        }

    return synthesis_node

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