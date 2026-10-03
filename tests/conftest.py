import pytest

from app.config import get_settings,Settings
import pytest

from app.main import create_app


@pytest.fixture(autouse=True)
def isolate_test_settings(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "fake")
    monkeypatch.setenv("TOOL_MODE", "demo")
    monkeypatch.setenv("CHECKPOINT_BACKEND", "memory")

    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def test_app():
    return create_app(
        Settings(
            agent_mode="fake",
            tool_mode="demo",
            checkpoint_backend="memory",
        ) # type: ignore
    )