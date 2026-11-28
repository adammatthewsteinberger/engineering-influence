# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Loads the prompt templates that ship inside the package."""

import tomllib
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.prompt_library_interface import PromptLibraryInterface
from engineering_influence.models.prompt_template import PromptTemplate


class TomlPromptLibrary(PromptLibraryInterface):
    """One TOML file per template, in the package's ``templates`` folder.

    A file holds ``name`` (the same as the file name), ``version``, an optional ``description``,
    an optional ``untrusted`` list, and a ``[parts]`` table of text. Any other key is refused,
    so a misspelt ``untrusted`` cannot quietly leave a blank trusted.
    """

    KEYS = frozenset({"name", "version", "description", "untrusted", "parts"})

    def __init__(self, root: Traversable | None = None) -> None:
        """Remember the folder holding the template files, by default the package's templates."""
        self._root = root if root is not None else files(__package__).joinpath("templates")

    def names(self) -> list[str]:
        """Every template name, sorted."""
        suffix = ".toml"
        return sorted(
            entry.name[: -len(suffix)]
            for entry in self._root.iterdir()
            if entry.name.endswith(suffix)
        )

    def get(self, name: str) -> PromptTemplate:
        """The named template, or an ApplicationError (PROMPT_TEMPLATE_INVALID) when it is not valid."""
        if not PromptTemplate.NAME.fullmatch(name):
            raise self._invalid(f"{name!r} is not a template name")
        entry = self._root.joinpath(f"{name}.toml")
        try:
            data = tomllib.loads(entry.read_text(encoding="utf-8"))
        except OSError as error:
            raise self._invalid(f"there is no template named {name!r}") from error
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(f"template {name!r} is not valid TOML: {error}") from error
        return self._build(name, data)

    def _build(self, name: str, data: dict[str, Any]) -> PromptTemplate:
        unknown = sorted(data.keys() - self.KEYS)
        if unknown:
            raise self._invalid(f"template {name!r} has unknown keys {unknown}")
        if data.get("name") != name:
            raise self._invalid(f"template file {name!r}.toml names itself {data.get('name')!r}")
        try:
            return PromptTemplate(
                name=name,
                version=data["version"],
                parts=data["parts"],
                untrusted=frozenset(data.get("untrusted", [])),
                description=data.get("description", ""),
            )
        except KeyError as error:
            raise self._invalid(f"template {name!r} is missing {error.args[0]!r}") from error
        except (TypeError, ValueError, AttributeError) as error:
            raise self._invalid(f"template {name!r}: {error}") from error

    @staticmethod
    def _invalid(message: str) -> ApplicationError:
        return ApplicationError(code="PROMPT_TEMPLATE_INVALID", message=message, http_status=503)
