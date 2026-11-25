# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The readable text of a page, and its title."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.page_text_interface import PageTextInterface


@dataclass(frozen=True, slots=True)
class PageText(PageTextInterface):
    """What an extractor found: a title (possibly empty) and the text a reader would see."""

    title: str
    text: str

    def is_empty(self) -> bool:
        """True when there is no text a reader would see."""
        return not self.text.strip()
