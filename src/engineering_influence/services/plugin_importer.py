# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a Claude Code plugin folder and writes a plugin bundle for review."""

from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.plugin_folder_reader_interface import (
    PluginFolderReaderInterface,
)
from engineering_influence.interfaces.plugin_parser_interface import PluginParserInterface
from engineering_influence.interfaces.plugin_writer_interface import PluginWriterInterface
from engineering_influence.interfaces.skill_sink_interface import SkillSinkInterface
from engineering_influence.models.plugin_import_result import PluginImportResult
from engineering_influence.services.interfaces.plugin_folder_converter_interface import (
    PluginFolderConverterInterface,
)
from engineering_influence.services.interfaces.plugin_importer_interface import (
    PluginImporterInterface,
)


class PluginImporter(PluginImporterInterface):
    """Read, convert, write, and prove the file reads back: nothing more.

    The bundle is the format ``ei plugins add`` reads, so **the exact text and the exact server commands that
    would be installed can be read before anything is locked**. The bytes are parsed again before they are
    written, so a file this command writes is a file ``plugins show`` accepts. A bundle's name is its file's name,
    so a ``--out`` whose name differs is refused. Importing never locks, enables, runs or contacts anything, and
    never replaces a file.
    """

    def __init__(
        self,
        reader: PluginFolderReaderInterface,
        converter: PluginFolderConverterInterface,
        writer: PluginWriterInterface,
        parser: PluginParserInterface,
        sink: SkillSinkInterface,
        max_bytes: int,
    ) -> None:
        """Remember the reader, converter, writer and parser the import uses."""
        self._reader = reader
        self._converter = converter
        self._writer = writer
        self._parser = parser
        self._sink = sink
        self._max_bytes = max_bytes

    def import_plugin(
        self, source: Path, name: str | None, version: int, target: Path | None
    ) -> PluginImportResult:
        """Write the bundle file and say what it holds."""
        conversion = self._converter.convert(self._reader.read(source), name, version)
        plugin = conversion.plugin
        path = target or Path(f"{plugin.name}.toml")
        if path.name != f"{plugin.name}.toml":
            raise self._invalid(
                f"a plugin's name is its file's name, so the file is {plugin.name}.toml; "
                "choose another name with --name"
            )
        data = self._writer.render(plugin)
        if len(data) > self._max_bytes:
            raise self._invalid(
                f"the bundle would be {len(data):,} bytes and the lock reads at most {self._max_bytes:,}; "
                "the plugin has too much text"
            )
        if self._parser.parse(data, plugin.name) != plugin:
            raise self._invalid(
                "the bundle did not read back as it was written; nothing was written"
            )
        self._sink.write_new(path, data)
        return PluginImportResult(conversion, str(path))

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="PLUGIN_IMPORT_INVALID",
            message=f"the plugin cannot be imported: {why}",
            http_status=422,
        )
