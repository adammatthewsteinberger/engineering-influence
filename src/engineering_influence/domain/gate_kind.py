"""Gate kinds."""

from enum import StrEnum


class GateKind(StrEnum):
    """Whether a gate is evaluated automatically or by a person."""

    AUTO = "auto"
    HUMAN = "human"
