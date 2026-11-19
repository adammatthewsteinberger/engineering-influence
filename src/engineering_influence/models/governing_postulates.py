# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""User-supplied governing postulates."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoverningPostulates:
    """The project-specific principles required before Phase 1."""

    statements: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.statements or any(not statement.strip() for statement in self.statements):
            raise ValueError("governing postulates require at least one non-empty statement")
