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


def fake_research() -> SpecialistResult:
    return SpecialistResult(
        subtask_id="research",
        status="success",
        answer="The research specialist found supporting evidence.",
        evidence=[
            {
                "source": "demo-source",
                "detail": "This is deterministic demo evidence.",
            }
        ],
        assumptions=["The demo source is considered reliable."],
        confidence=0.85,
        tool_call_ids=[],
    )

def fake_analysis() -> SpecialistResult:
    return SpecialistResult(
        subtask_id="analysis",
        status="success",
        answer="The analysis specialist identified the main trade-offs.",
        evidence=[],
        assumptions=["The supplied research is representative."],
        confidence=0.8,
        tool_call_ids=[],
    )


def fake_review(
    results: dict[str, SpecialistResult],
) -> ReviewResult:
    if not results:
        decision = "escalate"
        feedback = ["No specialist results were produced."]
    else:
        decision = "approved"
        feedback = []

    return ReviewResult(
        subtask_id="workflow",
        decision=decision,
        quality_score=0.9 if decision == "approved" else 0.2,
        feedback=feedback,
        missing_evidence=[],
    )

def fake_synthesis(
    results: dict[str, SpecialistResult],
) -> FinalAnswer:
    evidence = []

    for result in results.values():
        evidence.extend(result.evidence)

    assumptions = []

    for result in results.values():
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