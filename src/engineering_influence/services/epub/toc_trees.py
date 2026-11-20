# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contents trees read from the EPUB 3 navigation document and from the NCX."""

from typing import Any

from defusedxml.ElementTree import fromstring

TocTree = list[tuple[str, str | None, Any]]


class TocTrees:
    """Nested (label, href, children) lists, so the two contents can be compared."""

    XHTML = "{http://www.w3.org/1999/xhtml}"
    NCX = "{http://www.daisy.org/z3986/2005/ncx/}"
    OPS_TYPE = "{http://www.idpf.org/2007/ops}type"

    def from_nav(self, nav: str) -> TocTree:
        """The EPUB 3 contents of a navigation document."""
        root = fromstring(nav.encode("utf-8"))
        toc = next(
            (n for n in root.iter(self.XHTML + "nav") if n.get(self.OPS_TYPE) == "toc"), None
        )
        return self._walk_nav(toc.find(self.XHTML + "ol") if toc is not None else None)

    def from_ncx(self, ncx: str) -> TocTree:
        """The NCX navMap."""
        root = fromstring(ncx.encode("utf-8"))
        return self._walk_ncx(root.find(self.NCX + "navMap"))

    def _walk_nav(self, ol: Any) -> TocTree:
        out: TocTree = []
        for li in ol.findall(self.XHTML + "li") if ol is not None else []:
            a = li.find(self.XHTML + "a")
            if a is None:
                raise ValueError("a navigation list item has no link")
            out.append(
                (
                    "".join(a.itertext()).strip(),
                    a.get("href"),
                    self._walk_nav(li.find(self.XHTML + "ol")),
                )
            )
        return out

    def _walk_ncx(self, parent: Any) -> TocTree:
        if parent is None:
            return []
        out: TocTree = []
        for point in parent.findall(self.NCX + "navPoint"):
            label = point.find(f"{self.NCX}navLabel/{self.NCX}text")
            content = point.find(self.NCX + "content")
            if label is None or content is None:
                raise ValueError("an NCX navPoint lacks its label or content")
            out.append(
                ("".join(label.itertext()).strip(), content.get("src"), self._walk_ncx(point))
            )
        return out
