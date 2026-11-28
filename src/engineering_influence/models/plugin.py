# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plugin: a reviewed bundle of tool server definitions and skills."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.plugin_interface import PluginInterface
from engineering_influence.models.plugin_server import PluginServer
from engineering_influence.models.skill import Skill


@dataclass(frozen=True, slots=True)
class Plugin(PluginInterface):
    """A name, a version, and the servers and skills it bundles. It grants nothing and runs nothing.

    Installing a plugin copies its **skills** into the skill lock, each enabled for no stage, and
    **prints** the commands that would lock its servers. It never starts a server or contacts one,
    and it never grants a tool or enables a skill for a stage: those are separate commands a person
    runs after reading what the bundle says (ADR 0008, decision 9). A bundle names at most
    ``MAX_SERVERS`` servers and ``MAX_SKILLS`` skills, each once, in name order, so what a person
    reviews is bounded and stable.
    """

    MAX_SERVERS: ClassVar[int] = 16
    MAX_SKILLS: ClassVar[int] = 16
    MAX_DESCRIPTION_CHARS: ClassVar[int] = 300

    name: str
    version: int
    description: str = ""
    servers: tuple[PluginServer, ...] = ()
    skills: tuple[Skill, ...] = ()

    def __post_init__(self) -> None:
        """Validate the plugin's name and version when it is built."""
        if not isinstance(self.name, str) or not Skill.NAME.fullmatch(self.name):
            raise ValueError("a plugin name is lowercase letters, digits and underscores")
        if type(self.version) is not int or self.version < 1:
            raise ValueError("a plugin version is a whole number from 1")
        if (
            not isinstance(self.description, str)
            or len(self.description) > self.MAX_DESCRIPTION_CHARS
            or not (self.description.isprintable() or self.description == "")
        ):
            raise ValueError(
                f"a description is one line of printable text, at most {self.MAX_DESCRIPTION_CHARS} characters"
            )
        if not isinstance(self.servers, tuple) or not isinstance(self.skills, tuple):
            raise TypeError("a plugin's servers and skills are tuples")
        if not self.servers and not self.skills:
            raise ValueError("a plugin bundles at least one server or one skill")
        if len(self.servers) > self.MAX_SERVERS or len(self.skills) > self.MAX_SKILLS:
            raise ValueError(
                f"a plugin bundles at most {self.MAX_SERVERS} servers and {self.MAX_SKILLS} skills"
            )
        server_names = [server.name for server in self.servers]
        skill_names = [skill.name for skill in self.skills]
        if server_names != sorted(set(server_names)) or skill_names != sorted(set(skill_names)):
            raise ValueError("a plugin names each server and each skill once, in name order")

    def identifier(self) -> str:
        """The name and version, as people write it: ``research_pack@1``."""
        return f"{self.name}@{self.version}"

    def server_names(self) -> tuple[str, ...]:
        """The names of the servers it describes, in order."""
        return tuple(server.name for server in self.servers)

    def skill_names(self) -> tuple[str, ...]:
        """The names of the skills it carries, in order."""
        return tuple(skill.name for skill in self.skills)
