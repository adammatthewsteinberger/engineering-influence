# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a kind of book reads to draft a chapter, how it labels it, and what it tells the model to do."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.draft_recipe_interface import DraftRecipeInterface


@dataclass(frozen=True, slots=True)
class DraftRecipe(DraftRecipeInterface):
    """The stages the draft reads (``inputs``), the labelled parts of the voice and the grounding, the templates
    that lay out a chapter's prompt and summarise a chapter, and the instruction.

    ``style`` and ``grounding`` are pairs of a label and an input; each renders as ``label:`` then the text, and the
    pairs are joined by a blank line. The outline is always an input, because the draft walks it. The instruction is
    the one piece of plain text the model is given, so it may hold only these blanks, each filled from a number or a
    closed set: ``{number}``, ``{count}``, ``{words}``, ``{violence}``, ``{heat}``, and for a sectioned draft
    ``{section}`` and ``{sections}``, the section's number and how many sections the chapter has.

    A sectioned draft writes each chapter as one call per beat (``sectioned=True``), so the instruction says which
    section and which beat to write. An unsectioned draft writes the whole chapter in one call, as novels do.
    """

    BLANKS: ClassVar[re.Pattern[str]] = re.compile(r"\{(\w+)\}")
    ALLOWED: ClassVar[frozenset[str]] = frozenset(
        {"number", "count", "words", "violence", "heat", "section", "sections"}
    )
    REQUIRED: ClassVar[frozenset[str]] = frozenset({"number", "count", "words"})
    SECTIONED: ClassVar[frozenset[str]] = frozenset({"section", "sections"})

    inputs: tuple[str, ...]
    style: tuple[tuple[str, str], ...]
    grounding: tuple[tuple[str, str], ...]
    context_template: str
    summary_template: str
    instruction: str
    sectioned: bool = False

    def __post_init__(self) -> None:
        if "outline" not in self.inputs or len(set(self.inputs)) != len(self.inputs):
            raise ValueError("a draft reads the outline, and each input once")
        for pairs in (self.style, self.grounding):
            if not pairs:
                raise ValueError("a draft needs a voice and a grounding")
            for label, stage in pairs:
                if not label.strip() or not label.isprintable() or stage not in self.inputs:
                    raise ValueError("a label is printable text and names an input")
        if not self.context_template.strip() or not self.summary_template.strip():
            raise ValueError("a draft needs a context template and a summary template")
        blanks = set(self.BLANKS.findall(self.instruction))
        required = self.REQUIRED | self.SECTIONED if self.sectioned else self.REQUIRED
        if blanks - self.ALLOWED or not required <= blanks:
            raise ValueError(
                "the instruction has the chapter number, count and words (and the section and "
                "sections when sectioned), and no other blank"
            )

    def style_text(self, texts: Mapping[str, str]) -> str:
        """The voice part of the context: each labelled input, in order."""
        return self._join(self.style, texts)

    def grounding_text(self, texts: Mapping[str, str]) -> str:
        """The part of the context the chapter is grounded in: each labelled input, in order."""
        return self._join(self.grounding, texts)

    def instruction_text(
        self,
        number: int,
        count: int,
        words: int,
        violence: str,
        heat: str,
        section: int = 1,
        sections: int = 1,
    ) -> str:
        """The one plain-text instruction for a chapter or section, from numbers and two closed-set levels."""
        return self.instruction.format(
            number=number,
            count=count,
            words=words,
            violence=violence,
            heat=heat,
            section=section,
            sections=sections,
        )

    @staticmethod
    def _join(pairs: tuple[tuple[str, str], ...], texts: Mapping[str, str]) -> str:
        return "\n\n".join(f"{label}:\n{texts[stage]}" for label, stage in pairs)
