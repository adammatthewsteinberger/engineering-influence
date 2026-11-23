# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for KdpListing."""

from abc import ABC, abstractmethod


class KdpListingInterface(ABC):
    """The listing a person pastes into KDP, rendered as markdown."""

    __slots__ = ()

    @abstractmethod
    def render(self, files: tuple[tuple[str, str, int, str], ...]) -> str:
        """Markdown with the listing fields, then the files in the bundle."""
