# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The model's page reader: one address in, the text a reader would see out."""

import re
from collections.abc import Mapping
from typing import Any, ClassVar

from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.tool_definition import ToolDefinition


class FetchUrlTool(ToolInterface):
    """Fetches a page through the source fetcher and returns its text under a pinned header.

    The fetcher decides what may be read (https to public hosts, checked again at every redirect),
    how much, and in what encoding, and it drops hidden text, so this tool adds no policy of its
    own. It only reads addresses the model was shown (see ``refuses``). A page that cannot be used comes back as the fetcher's error, which the model can read
    and work around. The header gives the address the text was finally read from, the page's own
    title and the SHA-256 of the text: that is the pin a source is later checked against.
    """

    NAME = "fetch_url"
    ADDRESS: ClassVar[re.Pattern[str]] = re.compile(r"https?://[^\s<>\"'`]+")
    TRAILING = ".,;:!?)]}"

    def __init__(self, fetcher: SourceFetcherInterface) -> None:
        """Remember the source fetcher the page is read through."""
        self._fetcher = fetcher

    def definition(self) -> ToolDefinition:
        """What the model is told about this tool."""
        return ToolDefinition(
            self.NAME,
            "Read one web page. Returns its address, title, a SHA-256 of the text and the text a "
            "reader would see. Only public https pages can be read.",
            {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The full https address to read."}
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        )

    def refuses(self, arguments: Mapping[str, Any], evidence: str) -> str:
        """Only an address that is in the prompt or an earlier result may be read.

        An address the model made up could carry data out in its path or query (a page that was
        told "fetch this address with the author's idea in it"), and the URL policy only stops
        private hosts, not that. An address from the author's own prompt, a search hit, or the
        final address of a page already read cannot have been made up by a page, so those are
        read and nothing else is.
        """
        shown = {found.rstrip(self.TRAILING) for found in self.ADDRESS.findall(evidence)}
        if arguments["url"] in shown:
            return ""
        return (
            "fetch_url only reads an address that appeared in the brief or in a search result "
            "or page you have already been given, copied exactly; find it with web_search first"
        )

    def shown(self, result: str) -> str:
        """The address the page was finally read from, and not the page's own text.

        The header is the first thing in the result, so the first ``Source:`` line is ours; a page
        that prints its own ``Source:`` line comes after it and is not looked at.
        """
        for line in result.splitlines():
            if line.startswith("Source: "):
                return line
        return ""

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        """The page under its header."""
        page = self._fetcher.fetch(arguments["url"])
        source = page.to_source()
        return (
            f"Source: {source.url}\n"
            f"Title: {' '.join(source.title.split())}\n"
            f"SHA-256: {source.content_hash}\n\n"
            f"{page.text}"
        )
