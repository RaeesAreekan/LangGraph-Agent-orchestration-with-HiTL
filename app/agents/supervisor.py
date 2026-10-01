from app.agents.base import StructuredModel
from app.agents.prompts import (
    SUPERVISOR_SYSTEM_PROMPT,
    build_supervisor_prompt,
)
from app.schemas.domain import ExecutionPlan


class SupervisorAgent:
    def __init__(self, model: StructuredModel) -> None:
        self.model = model

    async def run(
        self,
        original_task: str,
        user_id: str,
        request_context: dict,
        memories: list[str],
        specialist_names: list[str],
    ) -> ExecutionPlan:
        prompt = build_supervisor_prompt(
            original_task=original_task,
            user_id=user_id,
            request_context=request_context,
            memories=memories,
            specialist_names=specialist_names,
        )

        result = await self.model.ainvoke(
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
            user_prompt=prompt,
            output_type=ExecutionPlan,
        )

        return ExecutionPlan.model_validate(result)