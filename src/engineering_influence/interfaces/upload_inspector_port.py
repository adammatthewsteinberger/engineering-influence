# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Upload inspector port."""

from abc import ABC, abstractmethod

from engineering_influence.contracts.security_verdict import SecurityVerdict


class UploadInspectorPort(ABC):
    """Judge an untrusted upload before anything reads it."""

    @abstractmethod
    def inspect(self, filename: str, content_type: str | None, content: bytes) -> SecurityVerdict:
        """Return the verdict for one upload."""
