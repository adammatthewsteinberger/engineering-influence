# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The internal cover image is declared, present, a large RGB JPEG, and not shown on a page."""

import re

from engineering_influence.interfaces.epub_cover_inspector_interface import (
    EpubCoverInspectorInterface,
)
from engineering_influence.models.epub.epub_contents import EpubContents


class CoverCheck:
    """The Kindle Publishing Guidelines require an internal cover declared in the OPF."""

    def __init__(self, inspector: EpubCoverInspectorInterface) -> None:
        self._inspector = inspector

    def run(self, contents: EpubContents) -> list[str]:
        """Return problems with the cover declaration and image."""
        problems: list[str] = []
        opf_text = contents.opf_text
        item = re.search(r"<item\b(?=[^>]*properties=.[^'\"]*cover-image)[^>]*>", opf_text)
        if not item:
            problems.append('the OPF declares no cover image (properties="cover-image")')
        else:
            problems += self._image_problems(contents, item.group(0))
        pages = "".join(v for k, v in contents.docs.items() if k.endswith(".xhtml"))
        if re.search(r"<(?:img|svg)\b", pages):
            problems.append(
                "an XHTML page shows an image; KDP warns that an HTML cover page "
                "duplicates the cover"
            )
        return problems

    def _image_problems(self, contents: EpubContents, item: str) -> list[str]:
        problems: list[str] = []
        href_match = re.search(r"href=.([^'\"]+)", item)
        id_match = re.search(r"\bid=.([^'\"]+)", item)
        href = href_match.group(1) if href_match else ""
        cover_id = id_match.group(1) if id_match else ""
        if not re.search(r"media-type=.image/jpeg", item):
            problems.append("the cover image is not declared as image/jpeg")
        if not re.search(rf'<meta name="cover" content="{re.escape(cover_id)}"', contents.opf_text):
            problems.append('the OPF has no <meta name="cover"> pointing at the cover image')
        return problems + self._inspector.problems(contents, href)
