"""No stylesheet rule may hide an element."""

import re

from engineering_influence.publishing.epub.epub_contents import EpubContents


class StylesheetCheck:
    """Kindle cannot resolve a link whose target is, or sits inside, a hidden element.

    It also reads a descendant rule such as "h2 br { display: none }" as hiding the heading
    itself (E24010, "Hyperlink not resolved in toc"). Nothing in an ebook needs hiding.
    """

    def run(self, contents: EpubContents) -> list[str]:
        """Return a problem for each stylesheet that uses display:none."""
        return [
            f"{name} hides an element with display:none; Kindle then cannot resolve "
            "contents links to a heading it applies to"
            for name, css in contents.styles.items()
            if re.search(r"display\s*:\s*none", css)
        ]
