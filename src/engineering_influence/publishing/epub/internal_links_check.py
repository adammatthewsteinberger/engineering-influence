"""Every internal link resolves; no page has an empty title or empty paragraphs."""

import re

from engineering_influence.publishing.epub.epub_contents import EpubContents
from engineering_influence.publishing.epub.xhtml_patterns import XhtmlPatterns


class InternalLinksCheck:
    """Walks the XHTML pages checking hrefs, titles, and empty blocks."""

    def run(self, contents: EpubContents) -> list[str]:
        """Return problems found in the XHTML pages."""
        problems: list[str] = []
        ids = {
            name: set(XhtmlPatterns.ID.findall(data))
            for name, data in contents.docs.items()
            if name.endswith(".xhtml")
        }
        for name, data in contents.docs.items():
            if not name.endswith(".xhtml"):
                continue
            for target in re.findall(r"""\bhref=['"]([^'"]+)['"]""", data):
                if target.startswith(("http:", "https:", "mailto:")) or target.endswith(".css"):
                    continue
                file_part, _, anchor = target.partition("#")
                dest = contents.base + file_part if file_part else name
                if dest not in ids:
                    problems.append(f"{name} links to missing file {target}")
                elif anchor and anchor not in ids[dest]:
                    problems.append(f"{name} links to missing anchor {target}")
            if re.search(r"<title>\s*</title>", data):
                problems.append(f"{name} has an empty <title>")
            if XhtmlPatterns.EMPTY_BLOCK.search(data):
                problems.append(f"{name} has empty paragraphs")
        return problems
