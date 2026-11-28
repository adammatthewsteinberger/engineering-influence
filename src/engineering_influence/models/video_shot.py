# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One shot of a screenplay's video: the scene it comes from, the hosted model that makes it, its length and its prompt."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.video_shot_interface import VideoShotInterface


@dataclass(frozen=True, slots=True)
class VideoShot(VideoShotInterface):
    """`number` runs from 1 in script order; `scene` is the script scene it comes from; `duration` is 1 to 30 seconds."""

    number: int
    scene: int
    model_name: str
    duration: int
    prompt: str

    def __post_init__(self) -> None:
        if type(self.number) is not int or self.number < 1:
            raise ValueError("a shot is numbered from 1")
        if type(self.scene) is not int or self.scene < 1:
            raise ValueError("a shot belongs to a scene numbered from 1")
        if not self.model_name.strip():
            raise ValueError("a shot names its model")
        if type(self.duration) is not int or not 1 <= self.duration <= 30:
            raise ValueError("a shot runs from 1 to 30 seconds")
        if not self.prompt.strip():
            raise ValueError("a shot has a prompt")

    def model(self) -> str:
        """The model that makes the shot."""
        return self.model_name

    def seconds(self) -> int:
        """How many seconds the shot runs."""
        return self.duration
