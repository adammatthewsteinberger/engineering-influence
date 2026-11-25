# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SkillImporter: read, parse, convert, write, and nothing else; a file too big for the lock is refused first."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.infrastructure.skills.toml_skill_writer import TomlSkillWriter
from engineering_influence.interfaces.skill_sink_interface import SkillSinkInterface
from engineering_influence.interfaces.skill_source_interface import SkillSourceInterface
from engineering_influence.services.interfaces.skill_importer_interface import (
    SkillImporterInterface,
)
from engineering_influence.services.skill_converter import SkillConverter
from engineering_influence.services.skill_importer import SkillImporter
from engineering_influence.services.skill_markdown_parser import SkillMarkdownParser

TEXT = """---
name: research-methodology
description: A short reference.
domains: [research]
---

# Title

## Source Evaluation

Use CRAAP and SIFT.

## Database Searching

Use Boolean operators.
"""


class Source(SkillSourceInterface):
    def __init__(self, text: str = TEXT) -> None:
        self.text = text
        self.read_paths: list[Path] = []

    def read(self, path: Path) -> str:
        self.read_paths.append(path)
        return self.text


class Sink(SkillSinkInterface):
    def __init__(self) -> None:
        self.written: dict[Path, bytes] = {}

    def write_new(self, path: Path, data: bytes) -> None:
        self.written[path] = data


def importer(
    source: Source | None = None, sink: Sink | None = None, max_bytes: int = 64 * 1024
) -> tuple[SkillImporter, Source, Sink]:
    made_source, made_sink = source or Source(), sink or Sink()
    return (
        SkillImporter(
            made_source,
            SkillMarkdownParser(),
            SkillConverter(),
            TomlSkillWriter(),
            made_sink,
            max_bytes,
        ),
        made_source,
        made_sink,
    )


def written(sink: Sink, path: str) -> Mapping[str, object]:
    return {"bytes": sink.written[Path(path)]}


def test_it_is_a_skill_importer() -> None:
    assert isinstance(importer()[0], SkillImporterInterface)


def test_the_default_file_is_named_for_the_skill_and_the_result_says_what_it_holds() -> None:
    service, source, sink = importer()
    done = service.import_skill(Path("some/SKILL.md"), None, 1, ("research",), (), False, None)
    assert source.read_paths == [Path("some/SKILL.md")]
    assert list(sink.written) == [Path("research_methodology.toml")]
    assert done.path == "research_methodology.toml"
    assert done.skill.identifier() == "research_methodology@1"
    assert done.sections == ("Source Evaluation", "Database Searching")
    assert done.ignored == ("domains",) and done.description_shortened is False


def test_a_target_and_a_name_and_chosen_sections_are_used() -> None:
    service, _, sink = importer()
    done = service.import_skill(
        Path("s.md"),
        "mine",
        3,
        ("outline", "research"),
        ("source evaluation",),
        False,
        Path("out/mine.toml"),
    )
    assert list(sink.written) == [Path("out/mine.toml")]
    assert (done.skill.name, done.skill.version, done.path) == ("mine", 3, "out/mine.toml")
    assert done.sections == ("Source Evaluation",)
    assert done.skill.stages() == ("outline", "research")


def test_what_is_written_reads_back_as_exactly_the_skill_that_was_made() -> None:
    service, _, sink = importer()
    done = service.import_skill(Path("s.md"), None, 2, ("research",), (), False, None)
    reread = TomlSkillParser().parse(sink.written[Path(done.path)], done.skill.name)
    assert reread == done.skill


def test_a_description_that_had_to_be_shortened_is_said_to_be() -> None:
    long = TEXT.replace("A short reference.", "word " * 100)
    done = importer(Source(long))[0].import_skill(
        Path("s.md"), None, 1, ("research",), (), False, None
    )
    assert done.description_shortened is True and done.skill.description.endswith("...")


def test_a_file_larger_than_the_lock_reads_is_refused_before_anything_is_written() -> None:
    service, _, sink = importer(max_bytes=100)
    with pytest.raises(ApplicationError) as error:
        service.import_skill(Path("s.md"), None, 1, ("research",), (), False, None)
    assert (error.value.code, error.value.http_status) == ("SKILL_IMPORT_TOO_LARGE", 422)
    assert "the lock reads at most 100" in error.value.message
    assert sink.written == {}


def test_the_size_limit_is_inclusive() -> None:
    probe, _, sink = importer()
    probe.import_skill(Path("s.md"), None, 1, ("research",), (), False, None)
    size = len(next(iter(sink.written.values())))
    importer(max_bytes=size)[0].import_skill(Path("s.md"), None, 1, ("research",), (), False, None)
    with pytest.raises(ApplicationError):
        importer(max_bytes=size - 1)[0].import_skill(
            Path("s.md"), None, 1, ("research",), (), False, None
        )


@pytest.mark.parametrize(
    ("text", "code"),
    [("not a skill", "SKILL_MARKDOWN_INVALID"), (TEXT, "SKILL_IMPORT_INVALID")],
)
def test_a_file_that_cannot_be_read_or_converted_writes_nothing(text: str, code: str) -> None:
    service, _, sink = importer(Source(text))
    stages = ("research",) if code == "SKILL_MARKDOWN_INVALID" else ()
    with pytest.raises(ApplicationError) as error:
        service.import_skill(Path("s.md"), None, 1, stages, (), False, None)
    assert error.value.code == code
    assert sink.written == {}


# ------------------------------------------------------------------------- reference mode
def test_a_reference_import_writes_a_reference_table_that_reads_back_the_same() -> None:
    service, _, sink = importer()
    done = service.import_skill(Path("s.md"), None, 2, (), (), True, None)
    assert done.skill.parts == () and done.skill.section_titles() == (
        "Source Evaluation",
        "Database Searching",
    )
    assert done.sections == ("Source Evaluation", "Database Searching")
    text = sink.written[Path(done.path)].decode()
    assert "[parts]" not in text and "[reference]" in text
    assert TomlSkillParser().parse(sink.written[Path(done.path)], done.skill.name) == done.skill


def test_a_reference_import_with_a_stage_writes_nothing() -> None:
    service, _, sink = importer()
    with pytest.raises(ApplicationError) as error:
        service.import_skill(Path("s.md"), None, 1, ("research",), (), True, None)
    assert error.value.code == "SKILL_IMPORT_INVALID" and sink.written == {}


def test_a_reference_file_larger_than_the_lock_reads_is_refused_before_it_is_written() -> None:
    service, _, sink = importer(max_bytes=100)
    with pytest.raises(ApplicationError) as error:
        service.import_skill(Path("s.md"), None, 1, (), (), True, None)
    assert error.value.code == "SKILL_IMPORT_TOO_LARGE" and sink.written == {}
