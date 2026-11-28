# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One plugin a marketplace index lists: what it is called, where it is, and the hash it must have."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.plugin_index_entry_interface import (
    PluginIndexEntryInterface,
)
from engineering_influence.models.mcp_endpoint_url import McpEndpointUrl
from engineering_influence.models.skill import Skill


@dataclass(frozen=True, slots=True)
class PluginIndexEntry(PluginIndexEntryInterface):
    """A name, a version, a short description, an https address and the SHA-256 of the file at it.

    The entry is a **promise about bytes**, and nothing else: the address says where to download them
    and the hash says what they must be. Whatever comes back is checked against the hash before it is
    read as anything, so an index that points at the wrong file, or a server that serves another one,
    is refused. The address is held to the rules the tool lock uses for a remote server (https, a host,
    no user or password, no query string or fragment), which is why ``McpEndpointUrl`` checks it.
    Whether the host is somewhere a download may go is decided each time, by the URL policy.
    """

    SHA256: ClassVar[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
    MAX_DESCRIPTION_CHARS: ClassVar[int] = 300

    name: str
    version: int
    url: str
    sha256: str
    description: str = ""

    def __post_init__(self) -> None:
        """Validate the entry's name, version, address and digest when it is built."""
        if not isinstance(self.name, str) or not Skill.NAME.fullmatch(self.name):
            raise ValueError("a listed plugin's name is lowercase letters, digits and underscores")
        if type(self.version) is not int or self.version < 1:
            raise ValueError(
                f"plugin {self.name!r} has a version that is not a whole number from 1"
            )
        if not isinstance(self.sha256, str) or not self.SHA256.fullmatch(self.sha256):
            raise ValueError(f"plugin {self.name!r} has a hash that is not 64 lowercase hex digits")
        if (
            not isinstance(self.description, str)
            or len(self.description) > self.MAX_DESCRIPTION_CHARS
            or not (self.description.isprintable() or self.description == "")
        ):
            raise ValueError(
                f"plugin {self.name!r} has a description that is not one short line of printable text"
            )
        try:
            McpEndpointUrl(self.url)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"plugin {self.name!r} has an address that is not usable: {error}"
            ) from error

    def identifier(self) -> str:
        """The name and version, as people write it: ``research_pack@1``."""
        return f"{self.name}@{self.version}"
