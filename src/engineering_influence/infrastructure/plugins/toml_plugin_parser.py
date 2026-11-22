# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a plugin from TOML, strictly."""

import tomllib
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.plugin_parser_interface import PluginParserInterface
from engineering_influence.interfaces.skill_parser_interface import SkillParserInterface
from engineering_influence.models.plugin import Plugin
from engineering_influence.models.plugin_server import PluginServer
from engineering_influence.models.skill import Skill


class TomlPluginParser(PluginParserInterface):
    """A plugin file has ``name`` (the file's name without ``.toml``), ``version``, an optional
    ``description``, and any number of ``[[server]]`` and ``[[skill]]`` tables.

    A ``[[server]]`` has ``name`` and either ``command`` (a list, with an optional ``env`` list) or
    ``url`` (with an optional ``bearer_env``). A ``[[skill]]`` is a skill file's contents as a table, and
    is read by the same strict skill parser, so a skill in a bundle is held to exactly the rules a
    skill file is. Any other key, anywhere, is refused and named: there is no key for a grant, a stage
    to enable a skill for, or anything else that would let a bundle decide what a model may do.
    """

    KEYS = frozenset({"name", "version", "description", "server", "skill"})
    SERVER_KEYS = frozenset({"name", "command", "env", "url", "bearer_env"})

    def __init__(self, skills: SkillParserInterface) -> None:
        self._skills = skills

    def parse(self, data: bytes, name: str) -> Plugin:
        """The plugin, or an ApplicationError (PLUGIN_INVALID) saying why the file is not one."""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise self._invalid(name, "it is not UTF-8 text") from error
        try:
            raw = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(name, f"it is not valid TOML: {error}") from error
        unknown = sorted(raw.keys() - self.KEYS)
        if unknown:
            raise self._invalid(name, f"it has unknown keys {unknown}")
        if raw.get("name") != name:
            raise self._invalid(name, f"it names itself {raw.get('name')!r}, not {name!r}")
        servers = self._tables(name, raw, "server")
        skills = self._tables(name, raw, "skill")
        built_servers = [self._server(name, entry) for entry in servers]
        built_skills = [self._skill(name, entry) for entry in skills]
        try:
            return Plugin(
                name=name,
                version=raw["version"],
                description=raw.get("description", ""),
                servers=tuple(sorted(built_servers, key=lambda server: server.name)),
                skills=tuple(sorted(built_skills, key=lambda skill: skill.name)),
            )
        except KeyError as error:
            raise self._invalid(name, f"it is missing {error.args[0]!r}") from error
        except (TypeError, ValueError) as error:
            raise self._invalid(name, str(error)) from error

    def _tables(self, plugin: str, raw: dict[str, Any], key: str) -> list[dict[str, Any]]:
        found = raw.get(key, [])
        if not isinstance(found, list) or any(not isinstance(entry, dict) for entry in found):
            raise self._invalid(plugin, f"its {key} entries are [[{key}]] tables")
        return found

    def _server(self, plugin: str, entry: dict[str, Any]) -> PluginServer:
        label = entry.get("name", "?")
        unknown = sorted(entry.keys() - self.SERVER_KEYS)
        if unknown:
            raise self._invalid(plugin, f"server {label!r} has unknown keys {unknown}")
        try:
            return PluginServer(
                name=entry.get("name", ""),
                command=self._strings(entry.get("command", [])),
                env=self._strings(entry.get("env", [])),
                url=entry.get("url", ""),
                bearer_env=entry.get("bearer_env", ""),
            )
        except (TypeError, ValueError) as error:
            raise self._invalid(plugin, f"server {label!r}: {error}") from error

    def _skill(self, plugin: str, entry: dict[str, Any]) -> Skill:
        name = entry.get("name")
        if not isinstance(name, str):
            raise self._invalid(plugin, "every skill needs a name")
        try:
            return self._skills.table(entry, name)
        except ApplicationError as error:
            raise self._invalid(plugin, error.message) from error

    @staticmethod
    def _strings(value: Any) -> tuple[str, ...]:
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise TypeError("expected a list of text")
        return tuple(value)

    @staticmethod
    def _invalid(name: str, why: str) -> ApplicationError:
        return ApplicationError(
            code="PLUGIN_INVALID", message=f"plugin {name!r}: {why}", http_status=422
        )
