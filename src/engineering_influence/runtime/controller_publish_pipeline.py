# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lets a publishing controller stand in for the acceptance pipeline."""

from pathlib import Path
from typing import Any

from engineering_influence.controllers.interfaces.publishing_controller_interface import (
    PublishingControllerInterface,
)
from engineering_influence.interfaces.publish_pipeline_interface import PublishPipelineInterface


class ControllerPublishPipeline(PublishPipelineInterface):
    """``publish`` is the controller's own ``publish``, which runs the pipeline for its project.

    The audit stage reaches the publishing code only through this, so the stage and its adapter never name a
    controller, and the publishing libraries are imported only when an audit runs.
    """

    def __init__(self, controller: PublishingControllerInterface) -> None:
        """Remember the publishing controller whose publish runs the pipeline."""
        self._controller = controller

    def publish(
        self,
        slug: str,
        *,
        dpi: int = 90,
        audit_only: bool = False,
        no_render: bool = False,
        report_path: Path | None = None,
        strict_release: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        """The report and whether every gate passed."""
        return self._controller.publish(
            slug,
            dpi=dpi,
            audit_only=audit_only,
            no_render=no_render,
            report_path=report_path,
            strict_release=strict_release,
        )
