# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stage cannot continue until credit or quota is restored."""

from engineering_influence.errors.interfaces.capacity_exhausted_error_interface import (
    CapacityExhaustedErrorInterface,
)


class CapacityExhaustedError(CapacityExhaustedErrorInterface, RuntimeError):
    """Raise this when credit runs out or authentication fails; the run parks instead of failing."""
