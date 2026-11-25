"""Fixtures that give each integration test its own PostgreSQL schema and its own queues.

The tests need a real PostgreSQL and RabbitMQ: ``eval "$(sh tests/integration/stack.sh up)"`` starts
them and exports ``EI_TEST_DATABASE_URL`` and ``EI_TEST_RABBITMQ_URL``. Without those a test is
skipped, unless ``EI_REQUIRE_INTEGRATION=1``, which CI sets so a missing stack fails the run
instead of letting it pass with nothing tested.
"""

import asyncio
import os
import uuid
from collections.abc import Iterator

import aio_pika
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def required(name: str) -> str:
    """The value of a setting, or a skip (a failure when ``EI_REQUIRE_INTEGRATION=1``)."""
    value = os.environ.get(name, "").strip()
    if value:
        return value
    message = f"{name} is not set; start the stack with tests/integration/stack.sh"
    if os.environ.get("EI_REQUIRE_INTEGRATION") == "1":
        pytest.fail(message)
    pytest.skip(message)


@pytest.fixture
def postgres_url() -> Iterator[str]:
    """A URL whose ``search_path`` is a schema created for this test and dropped afterwards."""
    base = make_url(required("EI_TEST_DATABASE_URL"))
    schema = f"it_{uuid.uuid4().hex[:12]}"
    admin = create_engine(base)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = base.update_query_dict({"options": f"-csearch_path={schema}"})
    try:
        yield scoped.render_as_string(hide_password=False)
    finally:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def rabbitmq_url() -> str:
    """The broker's URL."""
    return required("EI_TEST_RABBITMQ_URL")


@pytest.fixture
def queue_name(rabbitmq_url: str) -> Iterator[str]:
    """A job queue name unique to this test; the queue and its dead-letter queue are deleted after."""
    name = f"it-{uuid.uuid4().hex[:12]}.jobs"
    yield name

    async def cleanup() -> None:
        connection = await aio_pika.connect_robust(rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            for queue in (name, f"{name}.dead"):
                await channel.queue_delete(queue)

    asyncio.run(cleanup())
