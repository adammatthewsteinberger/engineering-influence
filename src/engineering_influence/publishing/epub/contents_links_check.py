"""Every chapter, part, and back-matter piece has a working contents entry."""

import re

from engineering_influence.publishing.epub.epub_contents import EpubContents
from engineering_influence.publishing.epub.heading_ids import HeadingIds
from engineering_influence.publishing.typesetting.book import Book


class ContentsLinksCheck:
    """Counts the navigation entries and checks each target file, anchor, and heading id."""

    def run(self, contents: EpubContents, book: Book) -> list[str]:
        """Return problems with the navigation document's contents links."""
        problems: list[str] = []
        nav = contents.nav
        if not nav:
            problems.append("no navigation document found")
        toc = re.search(r"<nav[^>]*epub:type=.toc.[^>]*>(.*?)</nav>", nav, re.DOTALL)
        links = re.findall(
            r"<a href=.([^'\"#]+)(?:#([^'\"]+))?.[^>]*>(.*?)</a>",
            toc.group(1) if toc else "",
            re.DOTALL,
        )
        expected = len(book.front) + sum(1 + len(c) for _, c in book.parts) + len(book.back) + 1
        if len(links) != expected:
            problems.append(f"contents has {len(links)} entries, expected {expected}")
        for href, anchor, _label in links:
            target = contents.docs.get(contents.base + href)
            if target is None:
                problems.append(f"contents links to missing file {href}")
            elif anchor and f"id='{anchor}'" not in target and f'id="{anchor}"' not in target:
                problems.append(f"contents links to missing anchor {href}#{anchor}")
            elif anchor and anchor not in HeadingIds().own(target):
                # Kindle drops empty elements, anchors included; KDP then rejects the contents.
                problems.append(
                    f"contents link {href}#{anchor} does not target a heading element's own id"
                )
        return problems
