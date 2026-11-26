# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a Fountain screenplay: its title page, its elements and its scenes. Pure text in, values out."""

import re
from typing import ClassVar

from engineering_influence.models.fountain_block import FountainBlock
from engineering_influence.models.fountain_scene import FountainScene
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)


class FountainParser(FountainParserInterface):
    """The Fountain rules this pipeline relies on.

    A boneyard `/* ... */` is a comment and is removed. A note `[[...]]` is removed from the element it sits in,
    but kept on a scene heading as a note. A scene starts at a heading line (`INT.`, `EXT.`, `EST.`, `I/E`, or a
    leading `.`). Within a paragraph, a line that is all capitals followed by more lines is a cue, and the lines after
    it are parentheticals (in parentheses) or dialogue. `>TEXT<` is centred, `>TEXT` is a forced transition, and
    the standard transitions (`FADE IN:`, `CUT TO:`, `FADE OUT.` and the like) are transitions.
    """

    BONEYARD: ClassVar[re.Pattern[str]] = re.compile(r"/\*.*?\*/", re.DOTALL)
    NOTE: ClassVar[re.Pattern[str]] = re.compile(r"\[\[(.+?)\]\]", re.DOTALL)
    HEADING: ClassVar[re.Pattern[str]] = re.compile(
        r"^\s*(?:\.(?!\.)|(?:INT|EXT|EST|INT\./EXT|INT/EXT|I/E)[. ])", re.IGNORECASE
    )
    CENTERED: ClassVar[re.Pattern[str]] = re.compile(r"^>\s*(.*?)\s*<$")
    FORCED_TRANSITION: ClassVar[re.Pattern[str]] = re.compile(r"^>\s*(.*)$")
    TRANSITION: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?:[A-Z ]+ TO:|FADE IN:|FADE OUT\.|CUT TO BLACK\.|SMASH TO:)$"
    )

    def title_page(self, text: str) -> tuple[tuple[str, str], ...]:
        """The title page: `Key: value` lines up to the first blank line, with indented continuation lines."""
        if not text.startswith("Title:"):
            return ()
        pairs: list[tuple[str, str]] = []
        for line in text.split("\n\n", 1)[0].splitlines():
            if line[:1].isspace() and pairs:
                key, value = pairs[-1]
                pairs[-1] = (key, f"{value}\n{line.strip()}")
            elif ":" in line:
                key, value = line.split(":", 1)
                pairs.append((key.strip(), value.strip()))
        return tuple(pairs)

    def blocks(self, text: str) -> tuple[FountainBlock, ...]:
        """Every element after the title page."""
        blocks: list[FountainBlock] = []
        for paragraph in self._paragraphs(self._body(text)):
            blocks.extend(self._classify(self._without_notes(paragraph)))
        return tuple(blocks)

    def scenes(self, text: str) -> tuple[FountainScene, ...]:
        """Each heading line starts a scene that runs up to the next heading."""
        scenes: list[FountainScene] = []
        heading: str | None = None
        lines: list[str] = []
        for raw in self._body(text).splitlines():
            cleaned = self._without_notes([raw])
            if cleaned and self.HEADING.match(cleaned[0]):
                if heading is not None:
                    scenes.append(self._scene(len(scenes) + 1, heading, lines))
                heading, lines = raw, []
            elif heading is not None:
                lines.append(raw)
        if heading is not None:
            scenes.append(self._scene(len(scenes) + 1, heading, lines))
        return tuple(scenes)

    def _scene(self, number: int, heading: str, lines: list[str]) -> FountainScene:
        notes = tuple(self._note(content) for content in self.NOTE.findall(heading))
        clean = self._without_notes([heading])[0]
        blocks: list[FountainBlock] = []
        for paragraph in self._paragraphs("\n".join(lines)):
            blocks.extend(self._classify(self._without_notes(paragraph)))
        return FountainScene(number, clean, notes, tuple(blocks))

    def _body(self, text: str) -> str:
        """The script with the title page and boneyard comments taken out."""
        body = self.BONEYARD.sub("", text)
        if body.startswith("Title:"):
            body = body.split("\n\n", 1)[1] if "\n\n" in body else ""
        return body

    @staticmethod
    def _paragraphs(body: str) -> list[list[str]]:
        """The non-empty lines of each paragraph, where a paragraph is separated by a blank line."""
        paragraphs: list[list[str]] = []
        current: list[str] = []
        for line in body.splitlines():
            if line.strip():
                current.append(line.rstrip())
            elif current:
                paragraphs.append(current)
                current = []
        if current:
            paragraphs.append(current)
        return paragraphs

    def _without_notes(self, lines: list[str]) -> list[str]:
        """The lines with notes taken out, and the ones left empty dropped."""
        cleaned = (self.NOTE.sub("", line).strip() for line in lines)
        return [line for line in cleaned if line]

    def _classify(self, lines: list[str]) -> list[FountainBlock]:
        """Elements for one paragraph: a cue and its speech, or each line on its own kind."""
        if not lines:
            return []
        if len(lines) > 1 and self._is_cue(lines[0]):
            items: list[tuple[str, str]] = [("cue", lines[0])]
            for line in lines[1:]:
                items.append(("parenthetical" if line.startswith("(") else "dialogue", line))
        else:
            items = [(self._kind(line), self._content(line)) for line in lines]
        return self._group(items)

    def _is_cue(self, line: str) -> bool:
        return (
            line.startswith("@") or (line.isupper() and any(c.isalpha() for c in line))
        ) and not (self.HEADING.match(line) or line.startswith(">"))

    def _kind(self, line: str) -> str:
        if self.HEADING.match(line):
            return "heading"
        if self.CENTERED.match(line):
            return "centered"
        if self.FORCED_TRANSITION.match(line) or self.TRANSITION.match(line):
            return "transition"
        return "action"

    def _content(self, line: str) -> str:
        """The line without the Fountain marks that name its kind: `>` and `<` for centred or forced lines."""
        centred = self.CENTERED.match(line)
        if centred:
            return centred.group(1)
        if line.startswith(">"):
            return line[1:].strip()
        return line

    @staticmethod
    def _group(items: list[tuple[str, str]]) -> list[FountainBlock]:
        """Consecutive items of one kind become one block; a cue is always its own block.

        Callers pass at least one item, so the first item starts the first block.
        """
        kind, first = items[0]
        blocks: list[FountainBlock] = []
        run = [first]
        for item_kind, line in items[1:]:
            if item_kind == kind and kind != "cue":
                run.append(line)
            else:
                blocks.append(FountainBlock(kind, tuple(run)))
                kind, run = item_kind, [line]
        blocks.append(FountainBlock(kind, tuple(run)))
        return blocks

    @staticmethod
    def _note(content: str) -> tuple[str, str]:
        """`key: value` as a pair; a bare value is stored under `ref`."""
        if ":" in content:
            key, value = content.split(":", 1)
            return key.strip(), value.strip()
        return "ref", content.strip()
