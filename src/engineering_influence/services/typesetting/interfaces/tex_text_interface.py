# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TexText."""

from abc import ABC, abstractmethod


class TexTextInterface(ABC):
    """Escapes plain metadata, keeping line breaks."""

    __slots__ = ()

    @abstractmethod
    def text(self, s: str) -> str:
        """Render one metadata string."""

    @abstractmethod
    def paragraphs(self, s: str) -> str:
        """Render blank-line separated paragraphs."""

    @abstractmethod
    def url(self, s: str) -> str:
        """A URL or mail address safe inside \\url{} and \\href{}."""

    @abstractmethod
    def web_url(self, s: str) -> str:
        """A web address safe inside \\url{}, refusing any scheme but http and https."""

    @abstractmethod
    def pdf_info(self, s: str) -> str:
        """A string safe inside the PDF info dictionary after TeX has expanded it."""
