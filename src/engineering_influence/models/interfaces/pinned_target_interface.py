# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PinnedTarget."""

from abc import ABC, abstractmethod


class PinnedTargetInterface(ABC):
    """Where one outbound request really goes, and how to say who it is for."""

    __slots__ = ()

    @abstractmethod
    def request_headers(self) -> dict[str, str]:
        """The headers that keep the request addressed to the name the person wrote."""

    @abstractmethod
    def request_extensions(self) -> dict[str, str]:
        """The client extensions that keep the certificate checked against that name."""
