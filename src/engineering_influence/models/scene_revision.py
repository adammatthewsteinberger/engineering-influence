# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the revision stage did to one scene: its card, the word counts of the draft and the revision, and whether the draft was kept."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.scene_revision_interface import SceneRevisionInterface
from engineering_influence.models.scene_card import SceneCard


@dataclass(frozen=True, slots=True)
class SceneRevision(SceneRevisionInterface):
    """`draft_kept` is True when the stored revision is the draft unchanged, which is what the stage stores when the
    revision is rejected, unchanged, or left for want of money."""

    card: SceneCard
    draft_words: int
    revised_words: int
    draft_kept: bool

    def __post_init__(self) -> None:
        if type(self.draft_words) is not int or self.draft_words < 0:
            raise ValueError("a draft has a count of words, zero or more")
        if type(self.revised_words) is not int or self.revised_words < 0:
            raise ValueError("a revision has a count of words, zero or more")
        if type(self.draft_kept) is not bool:
            raise ValueError("a scene's draft is either kept or not")

    def status(self) -> str:
        """`draft kept` or `revised`."""
        return "draft kept" if self.draft_kept else "revised"
