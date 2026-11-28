# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lets a publishing controller stand in for the publish and package steps of a book."""

from typing import Any

from engineering_influence.controllers.interfaces.publishing_controller_interface import (
    PublishingControllerInterface,
)
from engineering_influence.interfaces.book_publisher_interface import BookPublisherInterface


class ControllerBookPublisher(BookPublisherInterface):
    """``publish`` and ``package`` are the controller's own, for its project.

    The build stage reaches the publishing code only through this, so the stage and its adapter never name a
    controller, and the publishing libraries are imported only when a book is built.
    """

    def __init__(self, controller: PublishingControllerInterface) -> None:
        """Remember the publishing controller for the project."""
        self._controller = controller

    def publish(
        self, slug: str, *, no_render: bool = False, strict_release: bool = False
    ) -> tuple[dict[str, Any], bool]:
        """The report and whether every gate passed."""
        return self._controller.publish(slug, no_render=no_render, strict_release=strict_release)

    def package(self, slug: str) -> str:
        """Write the release bundle."""
        return self._controller.package(slug)
