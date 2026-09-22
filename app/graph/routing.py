from app.schemas.domain import ExecutionPlan, SpecialistResult


def ready_subtasks(
    plan: ExecutionPlan,
    completed_ids: set[str],
) -> list:
    """
    Return subtasks whose dependencies are complete and which
    have not already completed.
    """
    return [
        subtask
        for subtask in plan.subtasks
        if subtask.id not in completed_ids
        and set(subtask.dependencies).issubset(completed_ids)
    ]


def merge_result_maps(
    left: dict[str, SpecialistResult],
    right: dict[str, SpecialistResult],
) -> dict[str, SpecialistResult]:
    """
    Merge specialist results safely.

    A later attempt may replace an earlier attempt.
    Conflicting results from the same attempt are rejected.
    """
    merged = dict(left)

    for subtask_id, incoming in right.items():
        existing = merged.get(subtask_id)

        if existing is None:
            merged[subtask_id] = incoming
            continue

        if incoming.attempt > existing.attempt:
            merged[subtask_id] = incoming
            continue

        if incoming.attempt < existing.attempt:
            raise ValueError(
                f"Cannot replace attempt {existing.attempt} with older "
                f"attempt {incoming.attempt} for '{subtask_id}'"
            )

        if incoming != existing:
            raise ValueError(
                f"Conflicting results for '{subtask_id}' "
                f"at attempt {incoming.attempt}"
            )

    return merged