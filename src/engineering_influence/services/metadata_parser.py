# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the metadata stage's markdown into a book's listing, strictly."""

import re
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.book_metadata import BookMetadata
from engineering_influence.services.interfaces.dash_rewriter_interface import (
    DashRewriterInterface,
)
from engineering_influence.services.interfaces.metadata_parser_interface import (
    MetadataParserInterface,
)


class MetadataParser(MetadataParserInterface):
    """The contract between the metadata stage and the stage that assembles the book.

    The stage is told to write ``Title:`` and ``Subtitle:`` (one line each), ``Description:`` (paragraphs),
    and ``Keywords:`` and ``Categories:`` (a bullet list each, one item to a line). A label may be bold. Text
    before the first label is ignored (a model's preamble). Each label appears once, and nothing in the
    keyword and category lists may be anything but a bullet, so a wrapped line cannot become half a keyword.

    Em and en dashes are rewritten first (see ``DashRewriter``) because the listing is printed in the book.
    What is left has to be a listing ``BookMetadata`` accepts: at least 80 words of description, exactly
    seven keywords and one to three categories that are browse paths. When it is not, the message says which
    rule it broke, so the person, or the stage that wrote it, can see why.
    """

    LABELS: ClassVar[tuple[str, ...]] = (
        "Title",
        "Subtitle",
        "Description",
        "Keywords",
        "Categories",
    )
    LABEL: ClassVar[re.Pattern[str]] = re.compile(
        r"^\s*\**\s*(title|subtitle|description|keywords|categories)\s*\**\s*:\s*\**\s*(.*?)\s*$",
        re.IGNORECASE,
    )
    BULLET: ClassVar[re.Pattern[str]] = re.compile(r"^\s*(?:[-*\u2022]|\d{1,2}[.)])\s+(\S.*?)\s*$")
    FRAME: ClassVar[str] = "*_\"'`\u201c\u201d"

    def __init__(self, dashes: DashRewriterInterface) -> None:
        self._dashes = dashes

    def parse(self, text: str) -> BookMetadata:
        """The listing."""
        sections = self._sections(self._dashes.rewrite(text))
        missing = [label for label in self.LABELS if label.lower() not in sections]
        if missing:
            raise self._invalid("it has no " + ", ".join(repr(label + ":") for label in missing))
        try:
            return BookMetadata(
                title=self._one_line("Title", sections["title"]),
                subtitle=self._one_line("Subtitle", sections["subtitle"]),
                description=self._paragraphs(sections["description"]),
                keywords=self._bullets("Keywords", sections["keywords"]),
                categories=self._bullets("Categories", sections["categories"]),
            )
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def _sections(self, text: str) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {}
        current: list[str] | None = None
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            found = self.LABEL.match(line)
            if found:
                name = found.group(1).lower()
                if name in sections:
                    raise self._invalid(f"it has two '{found.group(1).capitalize()}:' sections")
                current = sections.setdefault(name, [found.group(2)])
            elif current is not None:
                current.append(line)
        return sections

    def _one_line(self, label: str, lines: list[str]) -> str:
        values = [line.strip() for line in lines if line.strip()]
        if len(values) != 1:
            raise ValueError(f"{label.lower()} is one line, and this has {len(values)}")
        return values[0].strip(self.FRAME).strip()

    @staticmethod
    def _paragraphs(lines: list[str]) -> str:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(line.rstrip() for line in lines).strip())

    def _bullets(self, label: str, lines: list[str]) -> tuple[str, ...]:
        items = []
        for line in lines:
            if not line.strip():
                continue
            found = self.BULLET.match(line)
            if not found:
                raise ValueError(
                    f"every line under {label}: is a bullet point, and {line.strip()!r} is not"
                )
            items.append(found.group(1).strip(self.FRAME).strip())
        return tuple(items)

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="METADATA_INVALID",
            message=f"the metadata cannot be read: {why}",
            http_status=422,
        )
