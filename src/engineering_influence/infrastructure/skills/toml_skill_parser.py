# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a skill from TOML, strictly."""

import tomllib
from collections.abc import Mapping
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.skill_parser_interface import SkillParserInterface
from engineering_influence.models.skill import Skill


class TomlSkillParser(SkillParserInterface):
    """A skill file has ``name`` (the file's name without ``.toml``), ``version``, an optional
    ``description`` and a ``[parts]`` table of ``stage = "text"``.

    Any other key is refused, so a misspelt one cannot quietly change what a skill is, and a part
    that is not text is refused rather than turned into text. There is nothing else in the file for
    a model to be shown: no blanks, no tools, no commands.
    """

    KEYS = frozenset({"name", "version", "description", "parts", "reference"})

    def parse(self, data: bytes, name: str) -> Skill:
        """The skill, or an ApplicationError (SKILL_INVALID) saying why the file is not one."""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise self._invalid(name, "it is not UTF-8 text") from error
        try:
            raw = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(name, f"it is not valid TOML: {error}") from error
        return self.table(raw, name)

    def table(self, raw: Mapping[str, Any], name: str) -> Skill:
        """The skill in an already-read table, checked the same way a skill file is."""
        unknown = sorted(raw.keys() - self.KEYS)
        if unknown:
            raise self._invalid(name, f"it has unknown keys {unknown}")
        if raw.get("name") != name:
            raise self._invalid(name, f"it names itself {raw.get('name')!r}, not {name!r}")
        parts = raw.get("parts", {})
        if not isinstance(parts, dict) or any(not isinstance(text, str) for text in parts.values()):
            raise self._invalid(name, "its parts are a table of stage = text")
        reference = raw.get("reference", {})
        if not isinstance(reference, dict) or any(
            not isinstance(text, str) for text in reference.values()
        ):
            raise self._invalid(name, "its reference is a table of title = text")
        try:
            return Skill(
                name=name,
                version=raw["version"],
                parts=tuple(sorted(parts.items())),
                description=raw.get("description", ""),
                sections=tuple(reference.items()),
            )
        except KeyError as error:
            raise self._invalid(name, f"it is missing {error.args[0]!r}") from error
        except (TypeError, ValueError) as error:
            raise self._invalid(name, str(error)) from error

    @staticmethod
    def _invalid(name: str, why: str) -> ApplicationError:
        return ApplicationError(
            code="SKILL_INVALID", message=f"skill {name!r}: {why}", http_status=422
        )
