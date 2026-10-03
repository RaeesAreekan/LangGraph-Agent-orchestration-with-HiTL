from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


def to_psycopg_url(database_url: str) -> str:
    return database_url.replace(
        "postgresql+asyncpg://",
        "postgresql://",
        1,
    )


@asynccontextmanager
async def postgres_checkpointer(
    database_url: str,
) -> AsyncIterator[AsyncPostgresSaver]:
    connection_string = to_psycopg_url(database_url)

    async with AsyncPostgresSaver.from_conn_string(
        connection_string,
    ) as checkpointer:
        await checkpointer.setup()
        yield checkpointer