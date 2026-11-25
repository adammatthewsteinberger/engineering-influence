# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The editing passes of a novel: story, then lines, then copy."""

from typing import ClassVar

from engineering_influence.interfaces.revision_passes_interface import (
    RevisionPassesInterface,
)
from engineering_influence.models.revision_pass import RevisionPass


class NovelRevisionPasses(RevisionPassesInterface):
    """Three passes over a drafted novel, each narrower than the one before, and each keeping the story bible's names.

    **Story** sees the voice, the story bible, the whole outline, the beats, a line on every other chapter and this
    chapter, and may tighten scenes, sharpen goals and fix pacing, a fifth either way. **Lines** sees the voice and the
    chapter and edits sentence by sentence for rhythm, dialogue and point of view, a tenth either way. **Copy** sees the
    bible and the chapter and corrects spelling, grammar and consistency with the bible, a twentieth either way. Unlike a
    non-fiction book, a novel keeps its dashes: nothing here removes them. The first pass reads the drafted
    ``chapter_NN.md``, each next reads what the last wrote, and the book is assembled from the last.
    """

    PASSES: ClassVar[tuple[RevisionPass, ...]] = (
        RevisionPass(
            "revise_story",
            "novel_revise_story",
            "chapter",
            "story",
            (
                "voice",
                "bible",
                "outline",
                "summaries",
                "beats",
                "chapter",
                "words",
                "floor",
                "ceiling",
            ),
            0.8,
            1.2,
        ),
        RevisionPass(
            "revise_lines",
            "novel_revise_lines",
            "story",
            "lines",
            ("voice", "chapter", "words", "floor", "ceiling"),
            0.9,
            1.1,
        ),
        RevisionPass(
            "copy_edit",
            "novel_copy_edit",
            "lines",
            "copy",
            ("bible", "chapter", "words", "floor", "ceiling"),
            0.95,
            1.05,
        ),
    )

    def passes(self) -> tuple[RevisionPass, ...]:
        """The passes, in order."""
        return self.PASSES

    def final(self) -> str:
        """The file prefix the last pass writes."""
        return self.PASSES[-1].output
