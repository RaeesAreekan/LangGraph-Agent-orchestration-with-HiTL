import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_task_events_include_lifecycle_and_tool_events():
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        created = await client.post(
            "/tasks",
            json={
                "user_id": "demo-user",
                "task": "Prepare a research brief",
                "context": {},
            },
        )

        task_id = created.json()["task_id"]

        await app.state.executor.wait(task_id)

        response = await client.get(
            f"/tasks/{task_id}/events",
        )

    assert response.status_code == 200

    event_types = [
        event["event_type"]
        for event in response.json()
    ]

    assert "task_queued" in event_types
    assert "task_started" in event_types
    assert "tool_started" in event_types
    assert "tool_completed" in event_types
    assert "task_completed" in event_types