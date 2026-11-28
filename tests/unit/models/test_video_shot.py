# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""VideoShot: a shot names its model, its length (1 to 30 seconds) and its prompt, and refuses anything else."""

import pytest

from engineering_influence.models.video_shot import VideoShot


def test_a_shot_reports_its_model_and_length() -> None:
    shot = VideoShot(1, 2, "minimax/hailuo-3", 15, "a door")
    assert (shot.model(), shot.seconds(), shot.scene) == ("minimax/hailuo-3", 15, 2)


@pytest.mark.parametrize(
    ("number", "scene", "model", "duration", "prompt"),
    [
        (0, 1, "m", 5, "p"),
        (1, 0, "m", 5, "p"),
        (1, 1, "", 5, "p"),
        (1, 1, "m", 0, "p"),
        (1, 1, "m", 31, "p"),
        (1, 1, "m", 5, ""),
    ],
)
def test_an_invalid_shot_is_refused(
    number: int, scene: int, model: str, duration: int, prompt: str
) -> None:
    with pytest.raises(ValueError):
        VideoShot(number, scene, model, duration, prompt)
