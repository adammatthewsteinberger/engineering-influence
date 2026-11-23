# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Turns chosen sections of a SKILL.md into a skill for some stages."""

import re

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_document import SkillDocument
from engineering_influence.services.interfaces.skill_converter_interface import (
    SkillConverterInterface,
)


class SkillConverter(SkillConverterInterface):
    """The sections you choose, as one part of the skill for each stage you name, with the headings kept.

    Nothing is cut to fit. A part is at most the skill model's limit, and a SKILL.md is usually longer, so when the
    chosen text is too long the error lists every section with its length and says to choose with ``--section``.
    The name is the SKILL.md's, lower-cased with hyphens and spaces made underscores, unless you give one. The
    description is the SKILL.md's, cut at a word to the model's limit with ``...`` when it is longer (it is shown in
    lists and is never part of a prompt).
    """

    def convert(
        self,
        document: SkillDocument,
        name: str | None,
        version: int,
        stages: tuple[str, ...],
        titles: tuple[str, ...],
    ) -> Skill:
        """The skill."""
        if not stages:
            raise self._invalid("name at least one stage for the skill to speak to, with --stage")
        chosen = self._chosen(document, titles)
        text = "\n\n".join(f"## {title}\n\n{body}" for title, body in chosen)
        if len(text) > Skill.MAX_PART_CHARS:
            raise ApplicationError(
                code="SKILL_IMPORT_TOO_LARGE",
                message=(
                    f"the chosen text is {len(text):,} characters and a part holds at most "
                    f"{Skill.MAX_PART_CHARS:,}; choose sections with --section. The sections are: "
                    + "; ".join(f"{t!r} {len(b):,}" for t, b in document.sections)
                ),
                http_status=422,
            )
        try:
            return Skill(
                name=name or self._derive(document.name),
                version=version,
                parts=tuple((stage, text) for stage in sorted(set(stages))),
                description=self._describe(document.description),
            )
        except (ValueError, TypeError) as error:
            raise self._invalid(str(error)) from error

    def sections(self, document: SkillDocument, titles: tuple[str, ...]) -> tuple[str, ...]:
        """The titles of the chosen sections, in the order they appear."""
        return tuple(title for title, _ in self._chosen(document, titles))

    def _chosen(self, document: SkillDocument, titles: tuple[str, ...]) -> list[tuple[str, str]]:
        if not titles:
            return list(document.sections)
        wanted = {title.casefold() for title in titles}
        known = {title.casefold() for title in document.titles()}
        missing = sorted(title for title in titles if title.casefold() not in known)
        if missing:
            raise self._invalid(
                f"there is no section {missing[0]!r}; the sections are: "
                + "; ".join(repr(title) for title in document.titles())
            )
        return [(t, b) for t, b in document.sections if t.casefold() in wanted]

    @staticmethod
    def _derive(name: str) -> str:
        derived = re.sub(r"[-\s]+", "_", name.strip().lower())
        if not Skill.NAME.fullmatch(derived):
            raise SkillConverter._invalid(
                f"{name!r} cannot be made into a skill name (lowercase letters, digits and underscores, "
                "starting with a letter); give one with --name"
            )
        return derived

    @staticmethod
    def _describe(description: str) -> str:
        limit = Skill.MAX_DESCRIPTION_CHARS
        if len(description) <= limit:
            return description
        return description[: limit - 3].rsplit(" ", 1)[0].rstrip() + "..."

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="SKILL_IMPORT_INVALID",
            message=f"the skill cannot be imported: {why}",
            http_status=422,
        )
