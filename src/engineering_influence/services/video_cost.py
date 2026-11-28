# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The cost of the shots at the prices the research note gives, with a generation ratio for the takes not kept."""

from typing import ClassVar

from engineering_influence.models.video_shot import VideoShot
from engineering_influence.services.interfaces.video_cost_interface import VideoCostInterface


class VideoCost(VideoCostInterface):
    """Prices are at benchmark settings and change monthly (ADR 0015): re-check them before each production.
    `GENERATION_RATIO` is the takes generated for each second kept, three in the research note's planning mix."""

    MICRO_USD_PER_SECOND: ClassVar[dict[str, int]] = {
        "minimax/hailuo-3": 80_000,
        "alibaba/wan-3.0": 200_000,
        "google/gemini-omni-1.2-flash": 100_000,
    }
    GENERATION_RATIO: ClassVar[int] = 3

    def cost_micro_usd(self, shots: tuple[VideoShot, ...]) -> int:
        """The estimated cost of the shots, in micro-dollars."""
        return sum(
            self.GENERATION_RATIO * self.MICRO_USD_PER_SECOND[shot.model()] * shot.seconds()
            for shot in shots
        )
