# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A skill as written in a SKILL.md file."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.skill_document_interface import (
    SkillDocumentInterface,
)


@dataclass(frozen=True, slots=True)
class SkillDocument(SkillDocumentInterface):
    """The name and description from a SKILL.md's frontmatter and its body cut at the level-two headings.

    ``sections`` are ``(title, text)`` pairs in file order; text before the first heading is the section
    ``Overview``. ``ignored`` names the frontmatter keys that were read and set aside, because a skill
    here is text and grants nothing (``allowed-tools`` and the like).
    """

    name: str
    description: str
    sections: tuple[tuple[str, str], ...]
    ignored: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate the name, description and sections read from a SKILL.md."""
        for label, value in (("name", self.name), ("description", self.description)):
            if not isinstance(value, str) or not value.strip() or "\n" in value:
                raise ValueError(f"a skill document has a one-line {label}")
        if not isinstance(self.sections, tuple) or not self.sections:
            raise ValueError("a skill document has at least one section")
        for section in self.sections:
            if not isinstance(section, tuple) or len(section) != 2:
                raise TypeError("a section is a (title, text) pair")
            title, text = section
            if not isinstance(title, str) or not title.strip() or "\n" in title:
                raise ValueError("a section has a one-line title")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"the section {title!r} has text")
        folded = [title.casefold() for title, _ in self.sections]
        if len(set(folded)) != len(folded):
            raise ValueError("section titles differ, ignoring case")
        if not isinstance(self.ignored, tuple):
            raise TypeError("the ignored keys are a tuple")

    def titles(self) -> tuple[str, ...]:
        """The section titles, in order."""
        return tuple(title for title, _ in self.sections)

    def section(self, title: str) -> str | None:
        """The text of the section with this title, ignoring case, or None."""
        wanted = title.casefold()
        return next((text for found, text in self.sections if found.casefold() == wanted), None)
