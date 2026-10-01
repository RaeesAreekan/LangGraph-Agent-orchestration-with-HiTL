from app.agents.base import StructuredModel
from app.agents.prompts import (
    REVIEWER_SYSTEM_PROMPT,
    build_reviewer_prompt,
)
from app.schemas.domain import ReviewResult, SpecialistResult


class ReviewerAgent:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    async def run(
        self,
        original_task: str,
        specialist_results: dict[str, SpecialistResult],
        attempt: int,
    ) -> ReviewResult:
        prompt = build_reviewer_prompt(
            original_task=original_task,
            specialist_results={
                key: value.model_dump(mode="json")
                for key, value in specialist_results.items()
            },
            attempt=attempt,
        )

        result = await self.model.ainvoke(
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            user_prompt=prompt,
            output_type=ReviewResult,
        )

        result = result.model_copy(
            update={
                "subtask_id": "workflow",
            }
        )

        if result.decision == "needs_revision": # type: ignore
            if result.target_subtask_id is None: # type: ignore
                raise ValueError(
                    "Reviewer must specify a target_subtask_id "
                    "when requesting revision."
                )

            if result.target_subtask_id not in specialist_results: # type: ignore
                raise ValueError(
                    "Reviewer targeted an unknown subtask: "
                    f"{result.target_subtask_id}" # type: ignore
                )

        if result.decision in {"approved", "escalate"}: # type: ignore
            result = result.model_copy(
                update={
                    "target_subtask_id": None,
                }
            )

        return result # type: ignore