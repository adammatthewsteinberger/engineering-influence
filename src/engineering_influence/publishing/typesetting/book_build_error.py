"""Raised when a book cannot be built."""


class BookBuildError(RuntimeError):
    """A missing config or a failed LaTeX run."""
