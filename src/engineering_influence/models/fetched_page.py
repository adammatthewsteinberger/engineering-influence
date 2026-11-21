# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A page that was fetched and read, ready to be pinned as a source."""

import hashlib
from dataclasses import dataclass

from engineering_influence.models.interfaces.fetched_page_interface import FetchedPageInterface
from engineering_influence.models.source_record import SourceRecord


@dataclass(frozen=True, slots=True)
class FetchedPage(FetchedPageInterface):
    """The address a page was finally read from, its title and its text.

    ``url`` is the address after any redirects, because that is where the text came from. The text
    is untrusted: it is quoted to a model as evidence and never followed as instructions.
    """

    url: str
    title: str
    text: str

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("a fetched page has an address")
        if not self.text.strip():
            raise ValueError("a page with no text is not evidence")

    def content_hash(self) -> str:
        """The SHA-256 of the text, which is what the source is pinned by."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def to_source(self) -> SourceRecord:
        """The source record for this page, not yet verified against any claim."""
        return SourceRecord(self.url, self.title.strip() or self.url, self.content_hash())
