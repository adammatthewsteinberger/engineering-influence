"""Ordered pipeline stages."""

from enum import StrEnum


class PipelineStage(StrEnum):
    """The top-level stages a project may select."""

    THESIS = "thesis"
    BOOK = "book"
    NOVEL = "novel"
    SCREENPLAY = "screenplay"
    HUB = "hub"
    SPOKES = "spokes"
    DISTRIBUTION = "distribution"
    PUBLISH = "publish"
