# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The environment handed to an MCP server: an allow-list, never a copy."""

import os
from collections.abc import Mapping
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.interfaces.server_environment_interface import (
    ServerEnvironmentInterface,
)


class ServerEnvironment(ServerEnvironmentInterface):
    """A server must not inherit the parent's secrets, so it gets a short list and what is named.

    - ``PATH``, ``LANG``, ``TZ``, ``SYSTEMROOT`` and ``LC_*`` are passed on as they are.
    - ``HOME`` and the temporary-directory variables point at the server's own throwaway directory,
      so a server that writes to them writes there, where its disk use is measured. This does not
      stop a server reading a file by its absolute path: it is not a sandbox.
    - Each name the lock lists is passed with its value from the environment; a name that is not set
      is an error, and the confined names cannot be listed.
    - Nothing else is passed: no API key, no token, nothing the lock does not name.
    """

    NAMES = frozenset({"PATH", "LANG", "TZ", "SYSTEMROOT"})
    PREFIXES = ("LC_",)
    CONFINED = ("HOME", "TMPDIR", "TEMP", "TMP")

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        """Remember the parent environment the server draws its allowed variables from, or none."""
        self._environ = os.environ if environ is None else environ

    def build(self, names: tuple[str, ...], workdir: Path) -> dict[str, str]:
        """The allow-listed variables, the confined ones and the named ones, as a new dict."""
        built = {
            name: value
            for name, value in self._environ.items()
            if name in self.NAMES or name.startswith(self.PREFIXES)
        }
        built.update(dict.fromkeys(self.CONFINED, str(workdir)))
        for name in names:
            if name in self.CONFINED:
                raise self._error(
                    "TOOL_ENV_RESERVED", f"{name} is set by the runner and cannot be passed on"
                )
            if name not in self._environ:
                raise self._error("TOOL_ENV_MISSING", f"the environment variable {name} is not set")
            built[name] = self._environ[name]
        return built

    @staticmethod
    def _error(code: str, message: str) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=422)
