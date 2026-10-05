import operator
from typing import Annotated, TypedDict

from app.graph.routing import merge_result_maps
from app.schemas.domain import (
    ExecutionPlan,
    FinalAnswer,
    ReviewResult,
    SpecialistResult,
    ApprovalDecision
)


class OrchestratorState(TypedDict, total=False):
    task_id: str
    trace_id: str
    user_id: str
    original_task: str
    request_context: dict

    memories: list[str]
    memory_ids_used: list[str]
    
    plan: ExecutionPlan | None

    completed_subtask_ids: Annotated[
        set[str],
        ## or_ is used to merge sets from multiple sources, ensuring that all completed subtask IDs are captured.
        operator.or_,
    ]

    specialist_results: Annotated[
        dict[str, SpecialistResult],
        merge_result_maps,
    ]

    review_results: dict[str, ReviewResult]
    # add will merge the list of review results from multiple sources, ensuring that all reviews are captured in the history.
    review_history: Annotated[
        list[ReviewResult],
        operator.add,
    ]
    review_attempt: int

    final_answer: FinalAnswer | None        
    errors: list[str]
    escalated: bool
    human_review_requested: bool
    approval_decision: ApprovalDecision | None
    approval_rejected: bool