import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from tests.conftest import test_app

@pytest.mark.asyncio
async def test_task_waits_for_approval_and_resumes(test_app):
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
                    "human_review_requested": True,
                },
            )

            task_id = created.json()["task_id"]

            await app.state.executor.wait(task_id)

            waiting = await client.get(f"/tasks/{task_id}")
            waiting_body = waiting.json()

            assert waiting_body["status"] == "waiting_approval"
            assert waiting_body["pending_approval"] is not None

            approval = await client.post(
                f"/tasks/{task_id}/approval",
                json={
                    "approval_id": waiting_body[
                        "pending_approval"
                    ]["approval_id"],
                    "decision": "approve",
                    "reviewer_id": "demo-reviewer",
                    "comment": "Approved.",
                },
            )

            assert approval.status_code == 202

            await app.state.executor.wait(task_id)

            completed = await client.get(f"/tasks/{task_id}")
            completed_body = completed.json()

            assert completed_body["status"] == "completed"
            assert completed_body["final_answer"] is not None