# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The model's web search: links and titles only."""

from collections.abc import Mapping
from typing import Any

from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.tool_definition import ToolDefinition


class WebSearchTool(ToolInterface):
    """Runs one search and lists what it found, best first, as a title and a link.

    It gives the model somewhere to look, not something to quote: a hit carries no snippet, so
    anything the book leans on has to be read with ``fetch_url`` first. The query leaves this
    machine for the search vendor, so a stage that has this tool should not put anything private
    in what it asks the model to search for.
    """

    NAME = "web_search"
    DEFAULT_COUNT = 5

    def __init__(self, search: SearchProviderInterface) -> None:
        self._search = search

    def definition(self) -> ToolDefinition:
        """What the model is told about this tool."""
        return ToolDefinition(
            self.NAME,
            "Search the web for pages about a topic. Returns a numbered list of titles and "
            "links, best first, and no page text: read a page with fetch_url before relying on it.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to look for, in a few words."},
                    "count": {
                        "type": "integer",
                        "description": f"How many links, 1 to 10 (default {self.DEFAULT_COUNT}).",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        )

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        """The numbered links for the query, or a line saying there were none."""
        count = arguments.get("count", self.DEFAULT_COUNT)
        hits = self._search.search(arguments["query"], count)
        if not hits:
            return "No results."
        return "\n".join(
            f"{number}. {' '.join(hit.title.split()) or hit.url}\n   {hit.url}"
            for number, hit in enumerate(hits, 1)
        )
