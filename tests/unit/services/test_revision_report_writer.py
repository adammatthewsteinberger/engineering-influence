# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""RevisionReportWriter: the revision log and the source mapping follow the locked script's order, omitted scenes
included, and a scene with no revision recorded is refused."""

import pytest

from engineering_influence.models.scene_card import SceneCard
from engineering_influence.models.scene_revision import SceneRevision
from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.shooting_lock_entry import ShootingLockEntry
from engineering_influence.services.revision_report_writer import RevisionReportWriter

WRITER = RevisionReportWriter()
LOCK = ShootingLock(
    (
        ShootingLockEntry(1, "1", False),
        ShootingLockEntry(2, "42A", False),
        ShootingLockEntry(3, "43", True),
    )
)
SCENES = (
    SceneRevision(SceneCard(1, "Opening Image", "a", (1,)), 100, 100, True),
    SceneRevision(SceneCard(2, "Set-Up", "b", (2, 10)), 120, 110, False),
)


def test_the_log_lists_each_scene_with_its_status_and_word_counts() -> None:
    assert WRITER.revision_log(LOCK, SCENES) == (
        "# Revision log\n\n"
        "| Scene | Card | Status | Draft words | Revised words |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 1 | S01 | draft kept | 100 | 100 |\n"
        "| 42A | S02 | revised | 120 | 110 |\n"
        "| 43 | S03 | omitted | | |\n"
    )


def test_the_mapping_lists_each_scene_with_its_beat_and_sources() -> None:
    assert WRITER.source_mapping(LOCK, SCENES) == (
        "# Source mapping\n\n"
        "| Scene | Card | Beat | Sources |\n"
        "| --- | --- | --- | --- |\n"
        "| 1 | S01 | Opening Image | 001 |\n"
        "| 42A | S02 | Set-Up | 002, 010 |\n"
        "| 43 | S03 | omitted | |\n"
    )


def test_a_kept_scene_with_no_revision_recorded_is_refused() -> None:
    with pytest.raises(ValueError, match=r"\[2\]"):
        WRITER.revision_log(LOCK, SCENES[:1])
