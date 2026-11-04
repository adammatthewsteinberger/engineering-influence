"""User-supplied governing postulates."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoverningPostulates:
    """The project-specific principles required before Phase 1."""

    statements: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.statements or any(not statement.strip() for statement in self.statements):
            raise ValueError("governing postulates require at least one non-empty statement")
