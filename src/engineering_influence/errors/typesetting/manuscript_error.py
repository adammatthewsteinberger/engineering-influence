# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Raised when a manuscript cannot be converted."""

from engineering_influence.errors.typesetting.interfaces.manuscript_error_interface import (
    ManuscriptErrorInterface,
)


class ManuscriptError(ManuscriptErrorInterface, ValueError):
    """The manuscript breaks a rule of the print pipeline."""
