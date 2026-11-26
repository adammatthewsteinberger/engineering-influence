# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SceneRevision: the word counts are counts, and a scene's status says whether its revision was used."""

import pytest

from engineering_influence.models.scene_card import SceneCard
from engineering_influence.models.scene_revision import SceneRevision

CARD = SceneCard(1, "Set-Up", "body", (1,))


def test_a_kept_draft_reads_as_draft_kept() -> None:
    assert SceneRevision(CARD, 100, 100, True).status() == "draft kept"


def test_a_used_revision_reads_as_revised() -> None:
    assert SceneRevision(CARD, 100, 95, False).status() == "revised"


def test_word_counts_are_zero_or_more() -> None:
    with pytest.raises(ValueError, match="draft has a count of words"):
        SceneRevision(CARD, -1, 0, True)
    with pytest.raises(ValueError, match="revision has a count of words"):
        SceneRevision(CARD, 0, -1, True)


def test_a_draft_is_either_kept_or_not() -> None:
    with pytest.raises(ValueError, match="kept or not"):
        SceneRevision(CARD, 1, 1, 1)  # type: ignore[arg-type]
