# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a SKILL.md into a name, a description and sections, strictly."""

import json
import re
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.skill_document import SkillDocument
from engineering_influence.services.interfaces.skill_markdown_parser_interface import (
    SkillMarkdownParserInterface,
)


class SkillMarkdownParser(SkillMarkdownParserInterface):
    """A SKILL.md starts with a ``---`` block of ``key: value`` lines, then markdown.

    ``name`` and ``description`` are required and must each be on one line (quoted or not); a block scalar is
    refused rather than guessed at. Every other key (``allowed-tools``, ``domains``, a list under one) is read
    and **set aside**, never used, and named in the result, because a skill here is text and grants nothing.
    The body is cut at its level-two headings, outside code fences, so a ``##`` line inside a fence is not a
    heading. Text before the first heading (without the file's one level-one title) is the section
    ``Overview``; a heading with no text under it is dropped; two sections with the same title get ``(2)``,
    ``(3)`` and so on so each can be chosen.
    """

    FRONT: ClassVar[re.Pattern[str]] = re.compile(r"^---[ \t]*$")
    KEY: ClassVar[re.Pattern[str]] = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*)$")
    FENCE: ClassVar[re.Pattern[str]] = re.compile(r"^[ \t]*(```|~~~)")
    ONE: ClassVar[re.Pattern[str]] = re.compile(r"^#[ \t]+\S")
    TWO: ClassVar[re.Pattern[str]] = re.compile(r"^##[ \t]+(\S.*?)[ \t]*#*[ \t]*$")
    BLOCKS: ClassVar[frozenset[str]] = frozenset({"|", ">", "|-", ">-", "|+", ">+"})

    def parse(self, text: str) -> SkillDocument:
        """The document."""
        lines = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if not self.FRONT.match(lines[0]):
            raise self._invalid("it does not start with a --- frontmatter block")
        end = next((i for i in range(1, len(lines)) if self.FRONT.match(lines[i])), None)
        if end is None:
            raise self._invalid("its frontmatter block is never closed with ---")
        values, continued = self._frontmatter(lines[1:end])
        name = self._scalar("name", values, continued)
        description = self._scalar("description", values, continued)
        ignored = tuple(sorted(key for key in values if key not in ("name", "description")))
        sections = self._sections(lines[end + 1 :])
        if not sections:
            raise self._invalid("it has no text after the frontmatter")
        try:
            return SkillDocument(name, " ".join(description.split()), tuple(sections), ignored)
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def _frontmatter(self, lines: list[str]) -> tuple[dict[str, str], set[str]]:
        values: dict[str, str] = {}
        continued: set[str] = set()
        current: str | None = None
        for line in lines:
            if not line.strip():
                continue
            if line[0] in " \t-" and current is not None:
                continued.add(current)
                continue
            found = self.KEY.match(line)
            if found is None:
                raise self._invalid(f"the frontmatter line {line.strip()!r} is not 'key: value'")
            current = found.group(1)
            if current in values:
                raise self._invalid(f"the frontmatter has {current!r} twice")
            values[current] = found.group(2).strip()
        return values, continued

    def _scalar(self, key: str, values: dict[str, str], continued: set[str]) -> str:
        if key not in values:
            raise self._invalid(f"the frontmatter has no {key}")
        raw = values[key]
        if key in continued or raw in self.BLOCKS:
            raise self._invalid(f"the {key} runs over more than one line; put it on one line")
        return self._unquote(raw)

    @staticmethod
    def _unquote(raw: str) -> str:
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            if raw[0] == '"':
                try:
                    decoded = json.loads(raw)
                except ValueError:
                    return raw[1:-1]
                return str(decoded)
            return raw[1:-1].replace("''", "'")
        return raw

    def _sections(self, lines: list[str]) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        title: str | None = None
        buffer: list[str] = []
        fenced = seen_title = False

        def flush() -> None:
            body = "\n".join(buffer).strip()
            if body:
                sections.append((self._unique(title or "Overview", sections), body))

        for line in lines:
            if self.FENCE.match(line):
                fenced = not fenced
            elif not fenced:
                heading = self.TWO.match(line)
                if heading:
                    flush()
                    title, buffer = heading.group(1), []
                    continue
                if title is None and not seen_title and self.ONE.match(line):
                    seen_title = True
                    continue
            buffer.append(line)
        flush()
        return sections

    @staticmethod
    def _unique(title: str, taken: list[tuple[str, str]]) -> str:
        folded = {found.casefold() for found, _ in taken}
        candidate, number = title, 1
        while candidate.casefold() in folded:
            number += 1
            candidate = f"{title} ({number})"
        return candidate

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="SKILL_MARKDOWN_INVALID",
            message=f"the skill file cannot be read: {why}",
            http_status=422,
        )
