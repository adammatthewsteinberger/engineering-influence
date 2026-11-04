"""Ids on heading elements."""

from engineering_influence.publishing.epub.xhtml_patterns import XhtmlPatterns


class HeadingIds:
    """Finds the anchors a contents link may target."""

    def all(self, xhtml: str) -> list[str]:
        """Every id on or inside a heading element, in document order."""
        found: list[str] = []
        for match in XhtmlPatterns.HEADING.finditer(xhtml):
            found += XhtmlPatterns.ID.findall(match.group(2) + match.group(3))
        return found

    def own(self, xhtml: str) -> list[str]:
        """The id attribute of each heading element itself."""
        return [
            found
            for match in XhtmlPatterns.HEADING.finditer(xhtml)
            for found in XhtmlPatterns.ID.findall(match.group(2))
        ]
