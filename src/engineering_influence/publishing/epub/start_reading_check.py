"""Kindle needs a start-reading location."""

from engineering_influence.publishing.epub.epub_contents import EpubContents


class StartReadingCheck:
    """EPUB 3 landmarks and the EPUB 2 guide both name where reading begins."""

    def run(self, contents: EpubContents) -> list[str]:
        """Return problems with the start-of-text references."""
        problems: list[str] = []
        if 'epub:type="bodymatter"' not in contents.nav:
            problems.append("the navigation document has no bodymatter landmark")
        if '<reference type="text"' not in contents.opf_text:
            problems.append("the OPF has no guide reference for the start of the text")
        return problems
