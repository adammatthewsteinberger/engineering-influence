# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The environment handed to TeX and to tex4ebook: an allow-list, never a copy."""

import os
from collections.abc import Mapping

from engineering_influence.infrastructure.typesetting.interfaces.tool_environment_interface import (
    ToolEnvironmentInterface,
)


class ToolEnvironment(ToolEnvironmentInterface):
    """Model-written text reaches TeX, so the build tools must not inherit secrets.

    A copy of ``os.environ`` would hand every API key and token in the parent process to
    ``lualatex``, to ``tex4ht`` and to anything a document manages to run. Only the names
    TeX needs to find its tree, its fonts and a temporary directory are passed on.
    """

    NAMES = frozenset(
        {
            "PATH",
            "HOME",
            "LANG",
            "TZ",
            "TMPDIR",
            "TEMP",
            "TMP",
            "SYSTEMROOT",
            "JAVA_HOME",
        }
    )
    PREFIXES = ("LC_", "TEXMF", "TEXINPUTS", "OSFONTDIR", "TEX4HT", "LUAINPUTS", "TTFONTS")

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        """Remember the environment the build tools inherit; by default, none of the parent's secrets."""
        self._environ = os.environ if environ is None else environ

    def build(self, source_date_epoch: int | None = None) -> dict[str, str]:
        """The allow-listed variables, shell escape off, and SOURCE_DATE_EPOCH when one is given."""
        kept = {
            name: value
            for name, value in self._environ.items()
            if name in self.NAMES or name.startswith(self.PREFIXES)
        }
        # Model-written text reaches TeX, and shell escape would let it run a command. It is set here, never inherited.
        kept["shell_escape"] = "f"
        if source_date_epoch is not None:
            kept["SOURCE_DATE_EPOCH"] = str(source_date_epoch)
        return kept
