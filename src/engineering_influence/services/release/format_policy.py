# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which output formats a book declares."""

from typing import Any

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.typesetting.trim_size import TrimSize
from engineering_influence.services.release.interfaces.format_policy_interface import (
    FormatPolicyInterface,
)


class FormatPolicy(FormatPolicyInterface):
    """Keeps old books compatible: no [formats] table means no hardcover.

    A hardcover is refused at a trim size KDP does not offer one for.
    """

    def of(self, config: dict[str, Any]) -> dict[str, Any]:
        """The explicit format policy."""
        formats = config.get("formats", {})
        hardcover = bool(formats.get("hardcover", False))
        trim = TrimSize.for_name(config.get("trim_size"))
        if hardcover and not trim.hardcover:
            offered = ", ".join(n for n in TrimSize.names() if TrimSize.for_name(n).hardcover)
            raise ManuscriptError(
                f"KDP does not print a hardcover at the {trim.name} trim; "
                f"use {offered}, or turn formats.hardcover off"
            )
        return {
            "hardcover": hardcover,
            "hardcover_max_pages": int(formats.get("hardcover_max_pages", 550)),
        }
