from app.agents.base import StructuredModel
from app.agents.prompts import (
    SYNTHESIZER_SYSTEM_PROMPT,
    build_synthesizer_prompt,
)
from app.schemas.domain import (
    ExecutionPlan,
    FinalAnswer,
    ReviewResult,
    SpecialistResult,
)


class SynthesizerAgent:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    async def run(
        self,
        original_task: str,
        plan: ExecutionPlan,
        specialist_results: dict[str, SpecialistResult],
        review_results: dict[str, ReviewResult],
    ) -> FinalAnswer:
        prompt = build_synthesizer_prompt(
            original_task=original_task,
            plan=plan.model_dump(mode="json"),
            specialist_results={
                key: value.model_dump(mode="json")
                for key, value in specialist_results.items()
            },
            review_results={
                key: value.model_dump(mode="json")
                for key, value in review_results.items()
            },
        )

        result = await self.model.ainvoke(
            system_prompt=SYNTHESIZER_SYSTEM_PROMPT,
            user_prompt=prompt,
            output_type=FinalAnswer,
        )

        return FinalAnswer.model_validate(result)