# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The house rules for printed text, which differ between a novel and a non-fiction book."""

from dataclasses import dataclass

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.typesetting.interfaces.text_policy_interface import (
    TextPolicyInterface,
)


@dataclass(frozen=True, slots=True)
class TextPolicy(TextPolicyInterface):
    """What the editorial checks and the typesetter allow, for one kind of book.

    Non-fiction keeps the strict house style: no em dashes, no scene breaks, and the word
    ``Draft`` is never allowed. A novel may use em dashes (interruptions and asides are ordinary in
    dialogue), prints a ``---`` rule as a scene break, and may have a character say ``Draft`` inside
    quoted speech. En dashes stay forbidden for both.
    """

    kind: BookKind
    allows_em_dash: bool
    keeps_scene_breaks: bool
    allows_draft_in_dialogue: bool

    @classmethod
    def for_name(cls, name: str | None) -> "TextPolicy":
        """The policy for a config's ``kind`` setting; a book that sets none is non-fiction."""
        if name is None:
            kind = BookKind.NONFICTION
        else:
            try:
                kind = BookKind(name)
            except ValueError:
                raise ManuscriptError(
                    f"the book kind must be 'nonfiction', 'novel' or 'screenplay', not {name!r}"
                ) from None
        fiction = kind in (BookKind.NOVEL, BookKind.SCREENPLAY)
        return cls(kind, fiction, fiction, fiction)
