"""Every document is well-formed XML with no declared entities."""

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from engineering_influence.publishing.epub.epub_contents import EpubContents


class XmlCheck:
    """Parses each document and collects the reader-visible text of the XHTML pages."""

    def run(self, contents: EpubContents) -> tuple[list[str], str]:
        """Return (problems, the XHTML text joined by newlines)."""
        problems: list[str] = []
        text_parts: list[str] = []
        for name, data in contents.docs.items():
            if "<!ENTITY" in data:
                problems.append(f"{name} declares XML entities")
                continue
            try:
                root = fromstring(data.encode("utf-8"))
            except (ParseError, DefusedXmlException) as error:
                problems.append(f"{name} is not well-formed XML: {error}")
                continue
            if name.endswith(".xhtml"):
                text_parts.append(" ".join(root.itertext()))
        return problems, "\n".join(text_parts)
