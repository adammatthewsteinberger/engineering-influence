# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Rewrites the em and en dashes a non-fiction book may not print."""

import re
from typing import ClassVar

from engineering_influence.services.interfaces.dash_rewriter_interface import (
    DashRewriterInterface,
)


class DashRewriter(DashRewriterInterface):
    """A dash between two digits becomes a hyphen (``1990-1995``); any other dash becomes a comma.

    A dash at the start of a line, at the end of one, or just before punctuation is dropped without a
    comma, so ``he stopped --`` ends at ``he stopped``. Commas the writer put there are never touched. This is a
    plain edit and not a good one; the copy edit stage is where the sentences get reworked.
    """

    RANGE: ClassVar[re.Pattern[str]] = re.compile("(?<=\\d)\u2013(?=\\d)")
    DASH: ClassVar[re.Pattern[str]] = re.compile("[ \\t]*[\u2013\u2014][ \\t]*")
    LEADING: ClassVar[re.Pattern[str]] = re.compile("^[ \\t]*[\u2013\u2014][ \\t]*", re.MULTILINE)
    TRAILING: ClassVar[re.Pattern[str]] = re.compile(
        "[ \\t]*[\u2013\u2014][ \\t]*(?=[.,;:!?)\\]]|$)", re.MULTILINE
    )

    def rewrite(self, text: str) -> str:
        """The text with no em dash and no en dash in it."""
        text = self.RANGE.sub("-", text)
        text = self.LEADING.sub("", text)
        text = self.TRAILING.sub("", text)
        return self.DASH.sub(", ", text)
