from app.agents.base import StructuredModel
from app.agents.prompts import (
    RESEARCHER_SYSTEM_PROMPT,
    build_researcher_prompt,
)
from app.schemas.domain import SpecialistResult


class ResearcherAgent:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    async def run(
        self,
        original_task: str,
        search_results: list[dict[str, str]],
        attempt: int,
        feedback: list[str],
        tool_call_ids: list[str],
    ) -> SpecialistResult:
        prompt = build_researcher_prompt(
            original_task=original_task,
            search_results=search_results,
            feedback=feedback,
        )

        result = await self.model.ainvoke(
            system_prompt=RESEARCHER_SYSTEM_PROMPT,
            user_prompt=prompt,
            output_type=SpecialistResult,
        )

        return result.model_copy(
            update={
                "subtask_id": "research",
                "attempt": attempt,
                "tool_call_ids": tool_call_ids,
            }
        ) # type: ignore