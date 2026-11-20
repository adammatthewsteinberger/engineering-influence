# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One rendered page."""

from dataclasses import dataclass

from engineering_influence.models.qa.interfaces.page_record_interface import PageRecordInterface


@dataclass
class PageRecord(PageRecordInterface):
    """Where a page image is, how big it is, and whether it is visually blank."""

    page: int
    path: str
    width: int
    height: int
    bytes: int
    blank: bool
