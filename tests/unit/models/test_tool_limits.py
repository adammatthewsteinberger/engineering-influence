# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ToolLimits: three positive ceilings."""

import dataclasses

import pytest

from engineering_influence.models.tool_limits import ToolLimits


def test_limits_hold_their_three_values() -> None:
    limits = ToolLimits(timeout_seconds=1.5, max_memory_bytes=2, max_disk_bytes=3)
    assert (limits.timeout_seconds, limits.max_memory_bytes, limits.max_disk_bytes) == (1.5, 2, 3)


@pytest.mark.parametrize(
    "bad", [(0, 1, 1), (1, 0, 1), (1, 1, 0), (-1, 1, 1), (1, -1, 1), (1, 1, -1)]
)
def test_a_zero_or_negative_limit_is_refused(bad: tuple[float, int, int]) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        ToolLimits(*bad)


def test_limits_are_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        ToolLimits(1, 1, 1).timeout_seconds = 2  # type: ignore[misc]
