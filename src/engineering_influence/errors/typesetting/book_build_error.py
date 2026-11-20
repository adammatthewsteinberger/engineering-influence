# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Raised when a book cannot be built."""

from engineering_influence.errors.typesetting.interfaces.book_build_error_interface import (
    BookBuildErrorInterface,
)


class BookBuildError(BookBuildErrorInterface, RuntimeError):
    """A missing config or a failed LaTeX run."""
