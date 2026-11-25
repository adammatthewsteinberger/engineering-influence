# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plugin folder turned into a bundle, with what was left out and why."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.plugin_conversion_interface import (
    PluginConversionInterface,
)
from engineering_influence.models.plugin import Plugin


@dataclass(frozen=True, slots=True)
class PluginConversion(PluginConversionInterface):
    """The bundle, the pieces that were skipped (``(what, why)``), notes on what was changed, and what was set aside.

    Nothing skipped is hidden: each skipped server or skill is named with the reason, so a person can fix the
    folder or write the missing part by hand.
    """

    plugin: Plugin
    skipped: tuple[tuple[str, str], ...] = ()
    notes: tuple[str, ...] = ()
    set_aside: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.plugin, Plugin):
            raise TypeError("a conversion holds a plugin")
        for label, lines in (
            ("skipped", self.skipped),
            ("notes", self.notes),
            ("set aside", self.set_aside),
        ):
            if not isinstance(lines, tuple):
                raise TypeError(f"{label} is a tuple")
        if any(not isinstance(pair, tuple) or len(pair) != 2 for pair in self.skipped):
            raise TypeError("every skipped piece is a (what, why) pair")
