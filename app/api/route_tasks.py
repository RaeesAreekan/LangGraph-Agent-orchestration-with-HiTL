from fastapi import APIRouter, HTTPException, Request, status

from app.schemas.api import (
    TaskCreatedResponse,
    TaskRequest,
    TaskStatusResponse,
)

from app.schemas.domain import ExecutionEvent , ApprovalDecision

router = APIRouter()


@router.post(
    "/tasks",
    response_model=TaskCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_task(
    payload: TaskRequest,
    request: Request,
) -> TaskCreatedResponse:
    executor = request.app.state.executor

    task = await executor.submit(payload)

    return TaskCreatedResponse(
        task_id=task.task_id,
        trace_id=task.trace_id,
        status=task.status,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
)
async def get_task(
    task_id: str,
    request: Request,
) -> TaskStatusResponse:
    executor = request.app.state.executor

    task = await executor.get(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return TaskStatusResponse(
        task_id=task.task_id,
        trace_id=task.trace_id,
        status=task.status,
        final_answer=task.final_answer,
        pending_approval=task.pending_approval,
        error=task.error,
    )

@router.get(
    "/tasks/{task_id}/events",
    response_model=list[ExecutionEvent],
)
async def get_task_events(
    task_id: str,
    request: Request,
) -> list[ExecutionEvent]:
    executor = request.app.state.executor

    task = await executor.get(task_id)

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return executor.event_sink.list_for_task(task_id)


@router.post(
    "/tasks/{task_id}/approval",
    response_model=TaskStatusResponse,
    status_code=202,
)
async def approve_task(
    task_id: str,
    decision: ApprovalDecision,
    request: Request,
) -> TaskStatusResponse:
    executor = request.app.state.executor

    try:
        task = await executor.resume(
            task_id,
            decision,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return TaskStatusResponse(
        task_id=task.task_id,
        trace_id=task.trace_id,
        status=task.status,
        final_answer=task.final_answer,
        pending_approval=task.pending_approval,
        error=task.error,
    )