# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The model's page reader: one address in, the text a reader would see out."""

from collections.abc import Mapping
from typing import Any

from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.tool_definition import ToolDefinition


class FetchUrlTool(ToolInterface):
    """Fetches a page through the source fetcher and returns its text under a pinned header.

    The fetcher decides what may be read (https to public hosts, checked again at every redirect),
    how much, and in what encoding, and it drops hidden text, so this tool adds no policy of its
    own. A page that cannot be used comes back as the fetcher's error, which the model can read
    and work around. The header gives the address the text was finally read from, the page's own
    title and the SHA-256 of the text: that is the pin a source is later checked against.
    """

    NAME = "fetch_url"

    def __init__(self, fetcher: SourceFetcherInterface) -> None:
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
