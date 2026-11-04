"""Cleans the XHTML that TeX4ht writes so Kindle's converter keeps every contents target."""

import re

from engineering_influence.publishing.epub.xhtml_patterns import XhtmlPatterns


class XhtmlCleaner:
    """Drops empty stubs, hoists heading ids, and adds xml:lang."""

    def clean(self, xhtml: str) -> str:
        """Return cleaned XHTML.

        Empty paragraphs and navigation stubs go, heading ids move onto the headings, and the
        root element gets xml:lang as well as lang, for hyphenation and speech.
        """
        xhtml = XhtmlPatterns.EMPTY_BLOCK.sub("", xhtml)
        xhtml = XhtmlPatterns.HEADING.sub(self._hoist_heading_id, xhtml)
        # TeX4ht puts a <br /> between "Chapter One" and the title. The label is a block
        # already, and hiding the <br /> with display:none makes Kindle's converter treat the
        # whole chapter heading as hidden (E24010, "Hyperlink not resolved in toc"). Drop the
        # element instead.
        xhtml = XhtmlPatterns.CHAPTER_HEAD_BR.sub(r"\1", xhtml)
        match = re.search(r"<html\b[^>]*>", xhtml)
        if match and "xml:lang" not in match.group(0):
            lang = re.search(r"\blang=['\"]([^'\"]+)", match.group(0))
            tag = match.group(0)[:-1] + f' xml:lang="{lang.group(1) if lang else "en"}">'
            xhtml = xhtml[: match.start()] + tag + xhtml[match.end() :]
        return xhtml

    def _hoist_heading_id(self, match: re.Match[str]) -> str:
        """Move a heading's empty anchor onto the heading itself.

        Kindle's converter can drop empty elements, so contents links would lose their targets.
        """
        level, attrs, body = match.groups()
        if XhtmlPatterns.ID.search(attrs):
            return match.group(0)
        anchor = XhtmlPatterns.EMPTY_ANCHOR.search(body)
        if not anchor:
            return match.group(0)
        body = body[: anchor.start()] + body[anchor.end() :]
        return f"<h{level}{attrs} id='{anchor.group(2)}'>{body}</h{level}>"
