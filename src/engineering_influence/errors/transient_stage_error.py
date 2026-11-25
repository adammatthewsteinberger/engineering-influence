# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stage failed in a way that trying again may fix."""

from engineering_influence.errors.interfaces.transient_stage_error_interface import (
    TransientStageErrorInterface,
)


class TransientStageError(TransientStageErrorInterface, RuntimeError):
    """Raise this for a timeout, a rate limit or a server error; the run retries the stage."""
