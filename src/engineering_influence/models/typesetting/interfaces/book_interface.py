# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Book."""

from abc import ABC


class BookInterface(ABC):
    """Metadata plus front matter, parts of chapters, and back matter."""

    __slots__ = ()
