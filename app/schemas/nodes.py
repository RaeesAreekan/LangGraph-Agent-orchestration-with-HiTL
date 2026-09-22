from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.domain import (
    ExecutionPlan,
    FinalAnswer,
    ReviewResult,
    SpecialistResult,
    Subtask,
)


class PlanNodeInput(BaseModel):
    task_id: str
    user_id: str
    original_task: str
    request_context: dict[str, Any] = Field(default_factory=dict)
    memories: list[str] = Field(default_factory=list)
    specialist_names: list[str] = Field(default_factory=list)


class PlanNodeOutput(BaseModel):
    plan: ExecutionPlan
    memory_ids_used: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class SpecialistNodeInput(BaseModel):
    task_id: str
    original_task: str
    subtask: Subtask
    dependency_results: dict[str, SpecialistResult] = Field(
        default_factory=dict
    )
    reviewer_feedback: list[str] = Field(default_factory=list)


class SpecialistNodeOutput(BaseModel):
    result: SpecialistResult


class ReviewNodeInput(BaseModel):
    original_task: str
    plan: ExecutionPlan
    specialist_results: dict[str, SpecialistResult] = Field(
        default_factory=dict
    )


class ReviewNodeOutput(BaseModel):
    review: ReviewResult
    next_route: Literal["continue", "revise", "escalate"]


class SynthesisNodeInput(BaseModel):
    original_task: str
    plan: ExecutionPlan
    specialist_results: dict[str, SpecialistResult] = Field(
        default_factory=dict
    )
    review_results: dict[str, ReviewResult] = Field(default_factory=dict)


class SynthesisNodeOutput(BaseModel):
    final_answer: FinalAnswer