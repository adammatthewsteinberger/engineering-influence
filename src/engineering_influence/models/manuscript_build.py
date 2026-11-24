# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What building an assembled book into its finished files said: the files, the steps, and what went wrong."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.manuscript_build_interface import (
    ManuscriptBuildInterface,
)


@dataclass(frozen=True, slots=True)
class ManuscriptBuild(ManuscriptBuildInterface):
    """Whether the book built and passed every gate, and the evidence.

    ``errors`` are what stopped the release; ``warnings`` are what the author should look at. ``steps`` are
    ``(name, status)`` pairs in the order they ran. ``reports`` are the evidence files of the build (the
    publication report, the step logs) and ``book`` are the files of the KDP bundle (the finished interior,
    EPUB and covers, the listing and the manifest). Both are ``(name, bytes)`` pairs with plain names.
    """

    passed: bool
    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    steps: tuple[tuple[str, str], ...]
    reports: tuple[tuple[str, bytes], ...]
    book: tuple[tuple[str, bytes], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.passed, bool) or not self.status.strip():
            raise ValueError("a build says whether it passed and in what status")
        for label, values in (("errors", self.errors), ("warnings", self.warnings)):
            if not isinstance(values, tuple) or any(not text.strip() for text in values):
                raise ValueError(f"the {label} are a tuple of messages")
        for label, files in (("reports", self.reports), ("book", self.book)):
            names = [name for name, _ in files]
            if not isinstance(files, tuple) or len(set(names)) != len(names):
                raise ValueError(f"the {label} are a tuple of distinct names")
            if any(not name or "/" in name or name.startswith(".") for name in names):
                raise ValueError(f"a file of the {label} has a plain name, with no folder in it")
        if self.passed and self.errors:
            raise ValueError("a build with errors did not pass")
        if self.passed and not self.book:
            raise ValueError("a build that passed produced the files of the book")
