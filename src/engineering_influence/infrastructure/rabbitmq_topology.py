# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The queues the API publishes to and the worker consumes from."""

from typing import Any


class RabbitMqTopology:
    """A durable job queue whose rejected messages go to a dead-letter queue.

    Both sides declare it. Publishing to the default exchange with a routing key for a
    queue that does not exist silently drops the message, so the publisher must not
    assume the worker declared it first.
    """

    def __init__(self, queue_name: str = "engineering-influence.jobs") -> None:
        if not queue_name.strip():
            raise ValueError("queue name is required")
        self.queue_name = queue_name
        self.dead_queue_name = f"{queue_name}.dead"

    async def declare(self, channel: Any) -> Any:
        """Declare both queues (idempotent) and return the job queue."""
        await channel.declare_queue(self.dead_queue_name, durable=True)
        return await channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": self.dead_queue_name,
            },
        )
