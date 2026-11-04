"""The HTML contents page is separate from the navigation document and sits near the front."""

import html
import re

from engineering_influence.publishing.epub.epub_contents import EpubContents
from engineering_influence.publishing.epub.toc_trees import TocTree


class ContentsPageCheck:
    """The Kindle Publishing Guidelines want the toc nav in its own document, outside the
    reading order; the page the guide and the toc landmark name is an ordinary page near the
    front, listing the NCX's entries in the NCX's order."""

    def run(self, contents: EpubContents, ncx_tree: TocTree | None) -> list[str]:
        """Return problems with the spine, guide, landmark, and contents page."""
        problems: list[str] = []
        opf_text = contents.opf_text
        ids_to_href: dict[str, str] = {}
        for tag in re.findall(r"<item\b[^>]*>", opf_text):
            attrs = dict(re.findall(r"\b(id|href)=['\"]([^'\"]+)['\"]", tag))
            ids_to_href[attrs.get("id", "")] = attrs.get("href", "")
        spine = [
            ids_to_href.get(i, "") for i in re.findall(r"<itemref\b[^>]*idref=.([^'\"]+)", opf_text)
        ]
        nav_href = contents.nav_href
        if nav_href in spine:
            problems.append(
                f"the navigation document {nav_href} is in the spine; "
                "it must be separate from the contents page"
            )
        guide = re.search(r'<reference type="toc"[^>]*href="([^"]+)"', opf_text)
        landmark = re.search(r'<a epub:type="toc" href="([^"]+)"', contents.nav)
        page_href = guide.group(1) if guide else ""
        if not guide:
            problems.append("the OPF guide has no toc reference")
        if not landmark or landmark.group(1) != page_href:
            problems.append("the toc landmark and the OPF guide do not name the same contents page")
        if page_href == nav_href:
            problems.append("the contents page is the navigation document; KDP wants them separate")
        if page_href not in spine:
            problems.append(f"the contents page {page_href} is not in the spine")
            return problems
        page = contents.docs.get(contents.base + page_href, "")
        if re.search(r"<nav\b", page):
            problems.append("the contents page contains a <nav> element")
        ncx = contents.docs.get(contents.ncx_name, "")
        first_target = next(iter(re.findall(r'<content src="([^"#]+)', ncx)), "")
        if first_target in spine and spine.index(page_href) > spine.index(first_target):
            problems.append(
                "the contents page comes after the first chapter; KDP wants it at the front"
            )
        page_links = [
            (html.unescape(re.sub(r"<[^>]+>", "", text)).strip(), href)
            for href, text in re.findall(r'<a href="([^"]+)">(.*?)</a>', page, re.DOTALL)
        ]
        if ncx_tree is not None and page_links != self._flat(ncx_tree):
            problems.append("the contents page does not list the NCX's entries in the NCX's order")
        return problems

    def _flat(self, tree: TocTree) -> list[tuple[str, str | None]]:
        flattened: list[tuple[str, str | None]] = []
        for label, href, children in tree:
            flattened.append((label, href))
            flattened.extend(self._flat(children))
        return flattened
