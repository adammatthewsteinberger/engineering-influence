# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface of the asynchronous engineering-influence client."""

from abc import ABC, abstractmethod


class AsyncEngineeringInfluenceClientInterface(ABC):
    """Async counterpart to the synchronous typed client."""

    __slots__ = ()

    @abstractmethod
    async def start_pipeline(
        self,
        slug: str,
        title: str,
        postulates: tuple[str, ...],
        stages: tuple[str, ...],
    ) -> dict[str, str]:
        """Create a project and enqueue its first pipeline stage asynchronously."""

    @abstractmethod
    async def close(self) -> None:
        """Close the underlying async HTTP connection pool."""
