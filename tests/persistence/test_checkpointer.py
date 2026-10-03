from app.persistence.checkpointer import to_psycopg_url


def test_converts_sqlalchemy_asyncpg_url_to_psycopg_url():
    url = (
        "postgresql+asyncpg://postgres:postgres"
        "@localhost:5432/orchestrator"
    )

    result = to_psycopg_url(url)

    assert result == (
        "postgresql://postgres:postgres"
        "@localhost:5432/orchestrator"
    )