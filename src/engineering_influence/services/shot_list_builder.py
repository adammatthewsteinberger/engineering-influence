# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Plans a screenplay's video: how long each scene runs, which hosted model makes it, and how it is cut into shots."""

import math
from typing import ClassVar

from engineering_influence.models.fountain_scene import FountainScene
from engineering_influence.models.video_shot import VideoShot
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.shot_list_builder_interface import (
    ShotListBuilderInterface,
)


class ShotListBuilder(ShotListBuilderInterface):
    """Routing follows ADR 0015, in this order: a scene noted [[hero]] goes to Wan 3.0 in shots of up to 30 seconds; a
    scene with VOICE_SPEECHES or more spoken speeches goes to Gemini Omni Flash, which keeps a voice the same, in shots of
    up to 15 seconds; any other scene longer than 15 seconds goes to Wan 3.0; the rest go to MiniMax H3 in shots of up to
    15 seconds. A scene's length is its words at WORDS_PER_SECOND, at least MIN_SCENE_SECONDS. That is a planning figure,
    which the cost estimate and a pilot then check against real footage.
    """

    WORDS_PER_SECOND: ClassVar[float] = 2.5
    MIN_SCENE_SECONDS: ClassVar[int] = 4
    VOICE_SPEECHES: ClassVar[int] = 3
    PROMPT_CHARACTERS: ClassVar[int] = 2_000
    DEFAULT_MODEL: ClassVar[str] = "minimax/hailuo-3"
    HERO_MODEL: ClassVar[str] = "alibaba/wan-3.0"
    VOICE_MODEL: ClassVar[str] = "google/gemini-omni-1.2-flash"
    SHORT_SHOT: ClassVar[int] = 15
    LONG_SHOT: ClassVar[int] = 30

    def __init__(self, parser: FountainParserInterface) -> None:
        """Remember the Fountain parser the shot list is built from."""
        self._parser = parser

    def build(self, script: str) -> tuple[VideoShot, ...]:
        """The shots for the script's scenes, each scene split into shots no longer than the model allows."""
        shots: list[VideoShot] = []
        for scene in self._parser.scenes(script):
            model, longest = self._route(scene)
            seconds = self._seconds(scene)
            prompt = scene.text()[: self.PROMPT_CHARACTERS]
            count = math.ceil(seconds / longest)
            base, extra = divmod(seconds, count)
            for index in range(count):
                duration = base + (1 if index < extra else 0)
                shots.append(VideoShot(len(shots) + 1, scene.number, model, duration, prompt))
        return tuple(shots)

    def _seconds(self, scene: FountainScene) -> int:
        words = sum(len(block.text().split()) for block in scene.blocks)
        return max(self.MIN_SCENE_SECONDS, round(words / self.WORDS_PER_SECOND))

    def _route(self, scene: FountainScene) -> tuple[str, int]:
        if scene.note("hero") is not None or scene.note("ref") == "hero":
            return self.HERO_MODEL, self.LONG_SHOT
        speeches = sum(1 for block in scene.blocks if block.kind == "dialogue")
        if speeches >= self.VOICE_SPEECHES:
            return self.VOICE_MODEL, self.SHORT_SHOT
        if self._seconds(scene) > self.SHORT_SHOT:
            return self.HERO_MODEL, self.LONG_SHOT
        return self.DEFAULT_MODEL, self.SHORT_SHOT
