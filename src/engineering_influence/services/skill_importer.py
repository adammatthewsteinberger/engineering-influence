# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a SKILL.md and writes a skill file for review."""

from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.skill_sink_interface import SkillSinkInterface
from engineering_influence.interfaces.skill_source_interface import SkillSourceInterface
from engineering_influence.interfaces.skill_writer_interface import SkillWriterInterface
from engineering_influence.models.skill_import_result import SkillImportResult
from engineering_influence.services.interfaces.skill_converter_interface import (
    SkillConverterInterface,
)
from engineering_influence.services.interfaces.skill_importer_interface import (
    SkillImporterInterface,
)
from engineering_influence.services.interfaces.skill_markdown_parser_interface import (
    SkillMarkdownParserInterface,
)


class SkillImporter(SkillImporterInterface):
    """Read, parse, convert, write: and nothing more.

    The result is an ordinary skill file in the format ``ei skills add`` reads, written next to where you ran it (or
    where you say) so that **the exact text a model will see can be read before anything is locked**. Importing never
    locks, enables or runs anything, and never replaces a file. A skill file larger than the limit the lock reads is refused here, with the
    reason, instead of after you have committed to it.
    """

    def __init__(
        self,
        source: SkillSourceInterface,
        parser: SkillMarkdownParserInterface,
        converter: SkillConverterInterface,
        writer: SkillWriterInterface,
        sink: SkillSinkInterface,
        max_file_bytes: int,
    ) -> None:
        self._source = source
        self._parser = parser
        self._converter = converter
        self._writer = writer
        self._sink = sink
        self._max_bytes = max_file_bytes

    def import_skill(
        self,
        source: Path,
        name: str | None,
        version: int,
        stages: tuple[str, ...],
        titles: tuple[str, ...],
        target: Path | None,
    ) -> SkillImportResult:
        """Write the skill file and say what it holds."""
        document = self._parser.parse(self._source.read(source))
        skill = self._converter.convert(document, name, version, stages, titles)
        data = self._writer.render(skill)
        if len(data) > self._max_bytes:
            raise ApplicationError(
                code="SKILL_IMPORT_TOO_LARGE",
                message=(
                    f"the skill file would be {len(data):,} bytes and the lock reads at most "
                    f"{self._max_bytes:,}; name fewer stages or choose fewer sections"
                ),
                http_status=422,
            )
        path = target or Path(f"{skill.name}.toml")
        self._sink.write_new(path, data)
        return SkillImportResult(
            skill=skill,
            path=str(path),
            sections=self._converter.sections(document, titles),
            ignored=document.ignored,
            description_shortened=skill.description != document.description,
        )
