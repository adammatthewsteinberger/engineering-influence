# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The evidence record of one visual-QA render."""

from dataclasses import asdict, dataclass
from typing import Any

from engineering_influence.publishing.qa.page_record import PageRecord


@dataclass
class RenderReport:
    """Every page's size and blankness, plus the contact sheets that show them."""

    schema_version: int
    pdf: str
    output: str
    dpi: int
    page_count: int
    rendered_pages: int
    contact_sheets: list[str]
    pages: list[PageRecord]

    @property
    def blank_pages(self) -> list[int]:
        """Numbers of pages that are visually blank."""
        return [page.page for page in self.pages if page.blank]

    @property
    def unexpected_blank_pages(self) -> list[int]:
        """Pages in a blank run longer than the print pipeline permits (two)."""
        unexpected: list[int] = []
        run: list[int] = []
        for page in [*self.pages, PageRecord(0, "", 0, 0, 0, False)]:
            if page.blank:
                run.append(page.page)
                continue
            if len(run) > 2:
                unexpected.extend(run)
            run = []
        return unexpected

    def as_dict(self) -> dict[str, Any]:
        """A JSON-ready dictionary including the derived blank-page lists."""
        result = asdict(self)
        result["blank_pages"] = self.blank_pages
        result["unexpected_blank_pages"] = self.unexpected_blank_pages
        return result
