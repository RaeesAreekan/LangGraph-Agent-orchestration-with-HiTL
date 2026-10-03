import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from tests.conftest import test_app


@pytest.mark.asyncio
async def test_create_task_returns_identifiers(test_app):
    app = test_app
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/tasks",
                json={
                    "user_id": "demo-user",
                    "task": "Prepare a research brief",
                    "context": {},
                },
            )

        assert response.status_code == 202

        body = response.json()

        assert body["task_id"]
        assert body["trace_id"]


@pytest.mark.asyncio
async def test_task_reaches_completed_status(test_app):
    app = test_app
    async with LifespanManager(app):
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

            response = await client.get(f"/tasks/{task_id}")

        assert response.status_code == 200

        body = response.json()

        assert body["task_id"] == task_id
        assert body["status"] == "completed"
        assert body["final_answer"] is not None