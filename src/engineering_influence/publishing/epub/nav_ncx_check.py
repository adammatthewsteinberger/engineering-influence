# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The EPUB 3 contents and the NCX must agree."""

import re

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import ParseError

from engineering_influence.publishing.epub.epub_contents import EpubContents
from engineering_influence.publishing.epub.toc_trees import TocTree, TocTrees


class NavNcxCheck:
    """KDP rejects a book whose EPUB 3 contents and NCX disagree in any entry or level."""

    def run(self, contents: EpubContents) -> tuple[list[str], TocTree | None]:
        """Return (problems, the NCX tree, or None when a document could not be parsed)."""
        problems: list[str] = []
        trees = TocTrees()
        nav_tree: TocTree | None
        ncx_tree: TocTree | None
        try:
            nav_tree = trees.from_nav(contents.nav)
            ncx_tree = trees.from_ncx(contents.docs.get(contents.ncx_name, ""))
        except (ParseError, DefusedXmlException):
            nav_tree, ncx_tree = None, None
        if nav_tree != ncx_tree:
            problems.append(
                "the contents page and the NCX do not list the same entries at the same levels"
            )
        if re.search(r'epub:type="toc"\s+href="[^"]*#', contents.nav):
            problems.append(
                "the toc landmark points at an anchor; it must point at the contents file"
            )
        return problems, ncx_tree
