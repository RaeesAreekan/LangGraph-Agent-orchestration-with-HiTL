from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text , UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sqlalchemy import UniqueConstraint
class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(
        String( 100),
        primary_key=True,
    )

    trace_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    original_task: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    request_context: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    human_review_requested: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    final_answer: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    pending_approval: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
    index=True,
    )

    conversation_id: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
    index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_tasks_user_idempotency_key",
        ),
    )



class EventRecord(Base):
    __tablename__ = "execution_events"

    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    task_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    trace_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    component: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    parent_event_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    event_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )