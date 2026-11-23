# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Turns a Claude Code plugin folder into a bundle to review."""

import re

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.plugin import Plugin
from engineering_influence.models.plugin_conversion import PluginConversion
from engineering_influence.models.plugin_folder import PluginFolder
from engineering_influence.models.plugin_server import PluginServer
from engineering_influence.models.skill import Skill
from engineering_influence.services.interfaces.plugin_folder_converter_interface import (
    PluginFolderConverterInterface,
)
from engineering_influence.services.interfaces.skill_converter_interface import (
    SkillConverterInterface,
)
from engineering_influence.services.interfaces.skill_markdown_parser_interface import (
    SkillMarkdownParserInterface,
)


class PluginFolderConverter(PluginFolderConverterInterface):
    """Every skill becomes a reference skill, and every server is kept only if the tool lock would accept it.

    Skills are converted by the same SKILL.md rules as ``ei skills import --reference``, each enabled for no stage.
    A server is carried over when it is a command with an absolute executable that is not a launcher
    (``npx`` and the like are refused: they fetch code that cannot be hashed), or a streamable-HTTP address with no
    secret in it. Environment **values** and headers are never copied: only the *names* of environment
    variables, and a bearer token written as ``Bearer ${NAME}`` becomes ``bearer_env = "NAME"``. A server or skill
    that cannot be carried over is skipped and named with the reason, never silently dropped, and the bundle is
    refused when nothing is left.
    """

    BEARER = re.compile(r"Bearer \$\{([A-Z][A-Z0-9_]{0,63})\}")

    def __init__(
        self, markdown: SkillMarkdownParserInterface, skills: SkillConverterInterface
    ) -> None:
        self._markdown = markdown
        self._skills = skills

    def convert(self, folder: PluginFolder, name: str | None, version: int) -> PluginConversion:
        """The bundle and what could not be carried over."""
        skipped: list[tuple[str, str]] = []
        notes: list[str] = []
        servers = self._servers(folder, skipped, notes)
        skills = self._skill_list(folder, skipped)
        if not servers and not skills:
            raise ApplicationError(
                code="PLUGIN_IMPORT_EMPTY",
                message="nothing in the folder could be imported"
                + ("; " + "; ".join(f"{what}: {why}" for what, why in skipped) if skipped else ""),
                http_status=422,
            )
        try:
            plugin = Plugin(
                name=self._name(name or folder.name),
                version=version,
                description=self._describe(folder.description),
                servers=tuple(sorted(servers, key=lambda server: server.name)),
                skills=tuple(sorted(skills, key=lambda skill: skill.name)),
            )
        except (ValueError, TypeError) as error:
            raise ApplicationError(
                code="PLUGIN_IMPORT_INVALID",
                message=f"the plugin cannot be imported: {error}",
                http_status=422,
            ) from error
        return PluginConversion(plugin, tuple(skipped), tuple(notes), folder.set_aside)

    def _skill_list(self, folder: PluginFolder, skipped: list[tuple[str, str]]) -> list[Skill]:
        built: dict[str, Skill] = {}
        for label, text in folder.skills:
            try:
                skill = self._skills.convert(self._markdown.parse(text), None, 1, (), (), True)
            except ApplicationError as error:
                skipped.append((f"skill {label}", error.message))
                continue
            if skill.name in built:
                skipped.append((f"skill {label}", f"another skill is already named {skill.name!r}"))
            elif len(built) >= Plugin.MAX_SKILLS:
                skipped.append(
                    (f"skill {label}", f"a bundle holds at most {Plugin.MAX_SKILLS} skills")
                )
            else:
                built[skill.name] = skill
        return list(built.values())

    def _servers(
        self, folder: PluginFolder, skipped: list[tuple[str, str]], notes: list[str]
    ) -> list[PluginServer]:
        built: dict[str, PluginServer] = {}
        for label in sorted(folder.servers):
            name = re.sub(r"[_\s]+", "-", label.strip().lower())
            try:
                if name in built:
                    raise ValueError(f"another server is already named {name!r}")
                if len(built) >= Plugin.MAX_SERVERS:
                    raise ValueError(f"a bundle holds at most {Plugin.MAX_SERVERS} servers")
                built[name] = self._server(name, folder.servers[label], notes)
            except (ValueError, TypeError) as error:
                skipped.append((f"server {label}", str(error)))
        return list(built.values())

    def _server(self, name: str, entry: object, notes: list[str]) -> PluginServer:
        table = dict(entry) if isinstance(entry, dict) else {}
        if "url" in table:
            return self._remote(name, table)
        if "command" not in table:
            raise ValueError("it has neither a command nor an address")
        kind = table.get("type", "stdio")
        if kind != "stdio":
            raise ValueError(f"it is {kind!r}, and only commands and streamable HTTP are read")
        arguments = table.get("args", [])
        if not isinstance(arguments, list):
            raise TypeError("its args are a list")
        command = (table["command"], *arguments)
        if any(not isinstance(part, str) for part in command):
            raise TypeError("its command and args are text")
        if any("${" in part for part in command):
            raise ValueError(
                "its command uses ${...} placeholders, which are not expanded; "
                "write the real absolute path of an installed server"
            )
        env = table.get("env", {})
        if not isinstance(env, dict):
            raise TypeError("its env is a table")
        server = PluginServer(name=name, command=tuple(command), env=tuple(sorted(env)))
        if env:
            notes.append(
                f"server {name}: environment values were not copied; "
                f"ei passes the variables {', '.join(sorted(env))} from your environment"
            )
        return server

    def _remote(self, name: str, table: dict[str, object]) -> PluginServer:
        kind = table.get("type", "http")
        if kind != "http":
            raise ValueError(f"it is {kind!r}, and only commands and streamable HTTP are read")
        address = table["url"]
        headers = table.get("headers", {})
        if not isinstance(address, str) or not isinstance(headers, dict):
            raise TypeError("its url is text and its headers are a table")
        bearer = ""
        for header, value in headers.items():
            matched = self.BEARER.fullmatch(value) if isinstance(value, str) else None
            if str(header).lower() != "authorization" or matched is None:
                raise ValueError(
                    "it sets headers other than a bearer token read from an environment variable"
                )
            bearer = matched.group(1)
        return PluginServer(name=name, url=address, bearer_env=bearer)

    @staticmethod
    def _name(raw: str) -> str:
        derived = re.sub(r"[-\s]+", "_", raw.strip().lower())
        if not Skill.NAME.fullmatch(derived):
            raise ValueError(
                f"{raw!r} cannot be made into a plugin name "
                "(lowercase letters, digits and underscores, starting with a letter); give one with --name"
            )
        return derived

    @staticmethod
    def _describe(description: str) -> str:
        flat = " ".join("".join(c if c.isprintable() else " " for c in description).split())
        limit = Plugin.MAX_DESCRIPTION_CHARS
        if len(flat) <= limit:
            return flat
        return flat[: limit - 3].rsplit(" ", 1)[0].rstrip() + "..."
