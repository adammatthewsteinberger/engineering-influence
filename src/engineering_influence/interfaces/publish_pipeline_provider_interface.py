# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for obtaining the acceptance pipeline when one is needed."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.publish_pipeline_interface import PublishPipelineInterface


class PublishPipelineProviderInterface(ABC):
    """Supply a pipeline, set up on demand rather than when the project is loaded."""

    __slots__ = ()

    @abstractmethod
    def provide(self) -> PublishPipelineInterface:
        """Build the pipeline, loading cover plugins as the build does."""
