from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.domain import FinalAnswer


class TaskRequest(BaseModel):
    user_id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    human_review_requested: bool = False
    idempotency_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )


class TaskCreatedResponse(BaseModel):
    task_id: str
    trace_id: str
    status: Literal["queued", "running"]


class TaskStatusResponse(BaseModel):
    task_id: str
    trace_id: str
    status: Literal[
        "queued",
        "running",
        "waiting_approval",
        "completed",
        "failed",
        "escalated",
    ]
    final_answer: FinalAnswer | None = None
    error: str | None = None
    pending_approval: dict | None = None