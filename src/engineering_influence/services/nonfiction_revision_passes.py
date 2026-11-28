# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The editing passes of a non-fiction book: structure, then lines, then copy."""

from typing import ClassVar

from engineering_influence.interfaces.revision_passes_interface import (
    RevisionPassesInterface,
)
from engineering_influence.models.revision_pass import RevisionPass


class NonfictionRevisionPasses(RevisionPassesInterface):
    """Each pass edits more narrowly than the one before, and may change the chapter's length less.

    **Structure** sees the whole outline, a line on every other chapter and this chapter's beats, and may
    reorder and cut so the chapter does its job and does not repeat another (a fifth either way); in a long chapter it
    reorders within each part (see ``RevisionStageExecutor``). **Lines**
    sees the voice and the chapter and edits sentence by sentence, keeping the facts and the order (a tenth
    either way). **Copy** sees only the chapter and corrects spelling, grammar, punctuation and consistency
    (a twentieth either way). The first reads the drafted ``chapter_NN.md``; each next reads what the last wrote;
    the book is assembled from the last.
    """

    PASSES: ClassVar[tuple[RevisionPass, ...]] = (
        RevisionPass(
            "revise_structure",
            "stage_revise_structure",
            "chapter",
            "structure",
            ("outline", "summaries", "beats", "chapter", "words", "floor", "ceiling"),
            0.8,
            1.2,
        ),
        RevisionPass(
            "revise_lines",
            "stage_revise_lines",
            "structure",
            "lines",
            ("voice", "chapter", "words", "floor", "ceiling"),
            0.9,
            1.1,
        ),
        RevisionPass("copy_edit", "stage_copy_edit", "lines", "copy", ("chapter",), 0.95, 1.05),
    )

    def passes(self) -> tuple[RevisionPass, ...]:
        """The passes, in order."""
        return self.PASSES

    def final(self) -> str:
        """The file prefix the last pass writes."""
        return self.PASSES[-1].output
