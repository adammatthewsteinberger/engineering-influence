# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What importing a Claude Code plugin folder produced."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.plugin_import_result_interface import (
    PluginImportResultInterface,
)
from engineering_influence.models.plugin_conversion import PluginConversion


@dataclass(frozen=True, slots=True)
class PluginImportResult(PluginImportResultInterface):
    """The conversion and the path of the bundle file that was written."""

    conversion: PluginConversion
    path: str

    def __post_init__(self) -> None:
        """Validate the import result's fields when it is built."""
        if not isinstance(self.conversion, PluginConversion) or not self.path.strip():
            raise ValueError("an import wrote a file for a conversion")
