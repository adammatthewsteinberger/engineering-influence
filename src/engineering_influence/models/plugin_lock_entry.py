# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One installed plugin, as the plugin lock records it."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.plugin_lock_entry_interface import (
    PluginLockEntryInterface,
)
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.skill import Skill


@dataclass(frozen=True, slots=True)
class PluginLockEntry(PluginLockEntryInterface):
    """A plugin's name, version, the SHA-256 of its bundle, the servers it declared and the skills it installed.

    The hash pins the bundle a person reviewed, so a bundle that changes by one character is
    refused by ``ei plugins verify``. The skills are recorded with the hash each was locked under,
    so removing the plugin takes out only skills that are still exactly what it installed. The
    servers are only names: the plugin installed none of them, a person locked each with
    ``ei tools add``, and the tool lock is where they are pinned.
    """

    SHA256: ClassVar[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")

    name: str
    version: int
    sha256: str
    servers: tuple[str, ...] = ()
    skills: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not Skill.NAME.fullmatch(self.name):
            raise ValueError("a locked plugin's name is lowercase letters, digits and underscores")
        if type(self.version) is not int or self.version < 1:
            raise ValueError(
                f"plugin {self.name!r} has a version that is not a whole number from 1"
            )
        if not self._digest(self.sha256):
            raise ValueError(f"plugin {self.name!r} has a hash that is not 64 lowercase hex digits")
        if not isinstance(self.servers, tuple) or not isinstance(self.skills, tuple):
            raise TypeError("a plugin's servers and skills are tuples")
        if any(
            not isinstance(name, str) or not McpServerLock.NAME.fullmatch(name)
            for name in self.servers
        ):
            raise ValueError(f"plugin {self.name!r} lists a server that is not a server name")
        for pair in self.skills:
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TypeError("an installed skill is a (name, hash) pair")
        if any(not isinstance(n, str) or not Skill.NAME.fullmatch(n) for n, _ in self.skills):
            raise ValueError(f"plugin {self.name!r} lists a skill that is not a skill name")
        if any(not self._digest(digest) for _, digest in self.skills):
            raise ValueError(f"plugin {self.name!r} lists a skill hash that is not 64 hex digits")
        if list(self.servers) != sorted(set(self.servers)):
            raise ValueError(f"plugin {self.name!r} lists its servers once each, in order")
        skill_names = [name for name, _ in self.skills]
        if skill_names != sorted(set(skill_names)):
            raise ValueError(f"plugin {self.name!r} lists its skills once each, in order")

    def identity(self) -> str:
        """The plugin as people write it, with its hash: ``research_pack@1:<hash>``."""
        return f"{self.name}@{self.version}:{self.sha256}"

    @classmethod
    def _digest(cls, value: object) -> bool:
        return isinstance(value, str) and bool(cls.SHA256.fullmatch(value))
