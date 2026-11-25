# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PluginImporter writes a bundle that reads back as written, in a file named for the plugin, and nothing else."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.toml_plugin_parser import TomlPluginParser
from engineering_influence.infrastructure.plugins.toml_plugin_writer import TomlPluginWriter
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.interfaces.plugin_folder_reader_interface import (
    PluginFolderReaderInterface,
)
from engineering_influence.interfaces.plugin_parser_interface import PluginParserInterface
from engineering_influence.interfaces.skill_sink_interface import SkillSinkInterface
from engineering_influence.models.plugin import Plugin
from engineering_influence.models.plugin_folder import PluginFolder
from engineering_influence.models.skill import Skill
from engineering_influence.services.interfaces.plugin_importer_interface import (
    PluginImporterInterface,
)
from engineering_influence.services.plugin_folder_converter import PluginFolderConverter
from engineering_influence.services.plugin_importer import PluginImporter
from engineering_influence.services.skill_converter import SkillConverter
from engineering_influence.services.skill_markdown_parser import SkillMarkdownParser

SKILL_MD = "---\nname: research\ndescription: Searching.\n---\n\n## Sources\n\nJudge a source."


class Reader(PluginFolderReaderInterface):
    def __init__(self, folder: PluginFolder) -> None:
        self.folder = folder
        self.read_paths: list[Path] = []

    def read(self, path: Path) -> PluginFolder:
        self.read_paths.append(path)
        return self.folder


class Sink(SkillSinkInterface):
    def __init__(self) -> None:
        self.written: list[tuple[Path, bytes]] = []

    def write_new(self, path: Path, data: bytes) -> None:
        self.written.append((path, data))


class OtherPlugin(PluginParserInterface):
    def parse(self, data: bytes, name: str) -> Plugin:
        return Plugin("other", 1, skills=(Skill("a", 1, (), sections=(("T", "x"),)),))


def importer(
    sink: Sink,
    folder: PluginFolder | None = None,
    parser: PluginParserInterface | None = None,
    max_bytes: int = 512 * 1024,
) -> PluginImporter:
    made = folder or PluginFolder(
        "My Pack", "Does things", {"s": {"command": "/bin/x"}}, (("research", SKILL_MD),)
    )
    return PluginImporter(
        Reader(made),
        PluginFolderConverter(SkillMarkdownParser(), SkillConverter()),
        TomlPluginWriter(),
        parser or TomlPluginParser(TomlSkillParser()),
        sink,
        max_bytes,
    )


def test_it_is_an_importer() -> None:
    assert isinstance(importer(Sink()), PluginImporterInterface)


def test_it_reads_the_folder_and_writes_a_bundle_named_for_the_plugin() -> None:
    sink = Sink()
    made = importer(sink).import_plugin(Path("/some/folder"), None, 3, None)
    assert made.path == "my_pack.toml"
    ((path, data),) = sink.written
    assert path == Path("my_pack.toml")
    assert TomlPluginParser(TomlSkillParser()).parse(data, "my_pack") == made.conversion.plugin
    assert made.conversion.plugin.identifier() == "my_pack@3"


def test_the_reader_is_given_the_path_it_was_asked_about() -> None:
    reader = Reader(PluginFolder("p", "", {}, (("research", SKILL_MD),)))
    PluginImporter(
        reader,
        PluginFolderConverter(SkillMarkdownParser(), SkillConverter()),
        TomlPluginWriter(),
        TomlPluginParser(TomlSkillParser()),
        Sink(),
        512 * 1024,
    ).import_plugin(Path("/some/folder"), None, 1, None)
    assert reader.read_paths == [Path("/some/folder")]


def test_a_target_in_another_folder_is_used_as_long_as_it_is_named_for_the_plugin() -> None:
    sink = Sink()
    made = importer(sink).import_plugin(Path("/f"), None, 1, Path("/project/my_pack.toml"))
    assert made.path == "/project/my_pack.toml" and sink.written[0][0] == Path(
        "/project/my_pack.toml"
    )


def test_a_target_with_another_name_is_refused_because_a_bundles_name_is_its_files() -> None:
    sink = Sink()
    with pytest.raises(ApplicationError) as error:
        importer(sink).import_plugin(Path("/f"), None, 1, Path("/project/renamed.toml"))
    assert error.value.code == "PLUGIN_IMPORT_INVALID"
    assert "the file is my_pack.toml; choose another name with --name" in error.value.message
    assert sink.written == []


def test_a_bundle_larger_than_the_lock_reads_is_refused_and_not_written() -> None:
    sink = Sink()
    with pytest.raises(ApplicationError) as error:
        importer(sink, max_bytes=100).import_plugin(Path("/f"), None, 1, None)
    assert "at most 100" in error.value.message and "too much text" in error.value.message
    assert sink.written == []


def test_a_bundle_that_does_not_read_back_as_written_is_never_written() -> None:
    sink = Sink()
    with pytest.raises(ApplicationError) as error:
        importer(sink, parser=OtherPlugin()).import_plugin(Path("/f"), None, 1, None)
    assert "did not read back as it was written" in error.value.message
    assert sink.written == []


def test_a_folder_with_nothing_to_import_writes_nothing() -> None:
    sink = Sink()
    with pytest.raises(ApplicationError) as error:
        importer(sink, PluginFolder("p", "", {}, ())).import_plugin(Path("/f"), None, 1, None)
    assert error.value.code == "PLUGIN_IMPORT_EMPTY" and sink.written == []


def test_a_bundle_exactly_as_large_as_the_lock_reads_is_written_and_one_byte_more_is_not() -> None:
    probe = Sink()
    importer(probe).import_plugin(Path("/f"), None, 1, None)
    size = len(probe.written[0][1])
    fits = Sink()
    importer(fits, max_bytes=size).import_plugin(Path("/f"), None, 1, None)
    assert len(fits.written) == 1
    over = Sink()
    with pytest.raises(ApplicationError):
        importer(over, max_bytes=size - 1).import_plugin(Path("/f"), None, 1, None)
    assert over.written == []
