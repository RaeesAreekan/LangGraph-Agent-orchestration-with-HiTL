from typing import Literal

from pydantic import BaseModel, Field, model_validator

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

class Subtask(BaseModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    specialist: Literal["researcher", "analyst"]
    dependencies: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    expected_output: str = Field(min_length=1)
    risk_level: Literal["low", "medium", "high"] = "low"
    requires_approval: bool = False


class ExecutionPlan(BaseModel):
    summary: str = Field(min_length=1)
    subtasks: list[Subtask] = Field(min_length=1)
    estimated_complexity: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_dependencies(self) -> "ExecutionPlan":
        subtask_ids = [subtask.id for subtask in self.subtasks]

        if len(subtask_ids) != len(set(subtask_ids)):
            raise ValueError("Subtask IDs must be unique")

        known_ids = set(subtask_ids)

        for subtask in self.subtasks:
            if subtask.id in subtask.dependencies:
                raise ValueError(
                    f"Subtask '{subtask.id}' cannot depend on itself"
                )

            unknown_dependencies = set(subtask.dependencies) - known_ids

            if unknown_dependencies:
                raise ValueError(
                    f"Subtask '{subtask.id}' has unknown dependencies: "
                    f"{sorted(unknown_dependencies)}"
                )

        return self


class SpecialistResult(BaseModel):
    subtask_id: str = Field(min_length=1)
    status: Literal["success", "failed"]
    answer: str
    evidence: list[dict[str, str]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    tool_call_ids: list[str] = Field(default_factory=list)
    attempt: int = Field(default=1, ge=1)


class ReviewResult(BaseModel):
    subtask_id: str = Field(min_length=1)
    target_subtask_id: str | None = None
    decision: Literal["approved", "needs_revision", "escalate"]
    quality_score: float = Field(ge=0, le=1)
    feedback: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class FinalAnswer(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    evidence: list[dict[str, str]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class ExecutionError(BaseModel):
    code: str
    message: str
    component: str
    retryable: bool


class ExecutionEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    trace_id: str = ""
    event_type: str
    component: str
    status: str
    summary: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    parent_event_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    approval_id: str = Field(min_length=1)

    decision: Literal[
        "approve",
        "modify",
        "reject",
        "take_over",
    ]

    reviewer_id: str = Field(min_length=1)

    modification: str | None = None
    comment: str | None = None


