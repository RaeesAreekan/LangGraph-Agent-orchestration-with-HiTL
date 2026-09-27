from app.schemas.domain import (
    ExecutionPlan,
    FinalAnswer,
    ReviewResult,
    SpecialistResult,
)

def fake_plan() -> ExecutionPlan:
    return ExecutionPlan(
        summary="Research and analyze the requested topic",
        subtasks=[
            {
                "id": "research",
                "description": "Gather relevant evidence",
                "specialist": "researcher",
                "dependencies": [],
                "required_inputs": [],
                "expected_output": "Evidence and sources",
                "risk_level": "low",
                "requires_approval": False,
            },
            {
                "id": "analysis",
                "description": "Analyze the available evidence",
                "specialist": "analyst",
                "dependencies": [],
                "required_inputs": [],
                "expected_output": "Analysis and assumptions",
                "risk_level": "low",
                "requires_approval": False,
            },
        ], # type: ignore
        estimated_complexity="medium",
        confidence=0.9,
    )


def fake_research(
    search_results: list[dict[str, str]],
    attempt: int = 1,
    feedback: list[str] | None = None,
    tool_call_ids: list[str] | None = None,
) -> SpecialistResult:
    if attempt == 1:
        answer = "The research result needs stronger supporting evidence."
        confidence = 0.55
    else:
        answer = "The revised research result includes stronger evidence."
        confidence = 0.9

    return SpecialistResult(
        subtask_id="research",
        status="success",
        answer=answer,
        evidence=search_results,
        assumptions=[
            "The demo search results are considered reliable.",
        ],
        confidence=confidence,
        tool_call_ids=tool_call_ids or [],
        attempt=attempt,
    )
def fake_analysis(attempt: int = 1) -> SpecialistResult:
    return SpecialistResult(
        subtask_id="analysis",
        status="success",
        answer="The analysis specialist identified the main trade-offs.",
        evidence=[],
        assumptions=["The supplied research is representative."],
        confidence=0.8,
        tool_call_ids=[],
        attempt=attempt,
    )


def fake_review(
    results: dict[str, SpecialistResult],
    attempt: int,
) -> ReviewResult:
    if attempt == 1:
        return ReviewResult(
            subtask_id="workflow",
            target_subtask_id="research",
            decision="needs_revision",
            quality_score=0.6,
            feedback=[
                "Improve the research evidence before synthesis.",
            ],
            missing_evidence=[
                "At least one stronger supporting source.",
            ],
        ) # type: ignore

    return ReviewResult(
        subtask_id="workflow",
        target_subtask_id=None,
        decision="approved",
        quality_score=0.9,
        feedback=[],
        missing_evidence=[],
    ) # type: ignore


def fake_synthesis(
    results: dict[str, SpecialistResult],
) -> FinalAnswer:
    evidence = []
    assumptions = []

    for result in results.values():
        evidence.extend(result.evidence)
        assumptions.extend(result.assumptions)

    return FinalAnswer(
        title="Demo Research Brief",
        body=(
            "The research and analysis specialists completed their work. "
            "The combined result is ready for delivery."
        ),
        evidence=evidence,
        assumptions=assumptions,
        limitations=["This is a deterministic PoC result."],
        confidence=0.85,
    )