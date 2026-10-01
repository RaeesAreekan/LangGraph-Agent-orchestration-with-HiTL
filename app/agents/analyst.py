from app.agents.base import StructuredModel
from app.agents.prompts import (
    ANALYST_SYSTEM_PROMPT,
    build_analyst_prompt,
)
from app.schemas.domain import SpecialistResult


class AnalystAgent:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    async def run(
        self,
        original_task: str,
        request_context: dict,
        attempt: int,
        feedback: list[str],
    ) -> SpecialistResult:
        prompt = build_analyst_prompt(
            original_task=original_task,
            request_context=request_context,
            feedback=feedback,
        )

        result = await self.model.ainvoke(
            system_prompt=ANALYST_SYSTEM_PROMPT,
            user_prompt=prompt,
            output_type=SpecialistResult,
        )

        return result.model_copy(
            update={
                "subtask_id": "analysis",
                "attempt": attempt,
                "tool_call_ids": [],
            }
        ) # type: ignore