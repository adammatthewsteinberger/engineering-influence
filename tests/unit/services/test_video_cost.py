# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""VideoCost: each shot's seconds at its model's price, times the takes generated for each kept second."""

from engineering_influence.models.video_shot import VideoShot
from engineering_influence.services.video_cost import VideoCost


def test_the_cost_is_the_price_per_second_times_seconds_times_the_takes() -> None:
    shots = (
        VideoShot(1, 1, "minimax/hailuo-3", 5, "p"),
        VideoShot(2, 1, "alibaba/wan-3.0", 2, "p"),
        VideoShot(3, 2, "google/gemini-omni-1.2-flash", 3, "p"),
    )
    expected = VideoCost.GENERATION_RATIO * (80_000 * 5 + 200_000 * 2 + 100_000 * 3)
    assert VideoCost().cost_micro_usd(shots) == expected == 3_300_000


def test_no_shots_cost_nothing() -> None:
    assert VideoCost().cost_micro_usd(()) == 0
