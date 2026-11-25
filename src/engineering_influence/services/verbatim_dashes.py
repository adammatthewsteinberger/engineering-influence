# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Leaves a novel's dashes as the author's prose has them."""

from engineering_influence.services.interfaces.verbatim_dashes_interface import (
    VerbatimDashesInterface,
)


class VerbatimDashes(VerbatimDashesInterface):
    """Returns the text unchanged, because fiction may print em and en dashes.

    The typesetter refuses dashes only in non-fiction. In a novel an em dash is how a line of dialogue breaks off,
    so rewriting it into a comma, as ``DashRewriter`` does for a non-fiction chapter, would damage the prose.
    """

    def rewrite(self, text: str) -> str:
        """The text, exactly as given."""
        return text
