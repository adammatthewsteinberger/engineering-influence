# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What importing a SKILL.md produced."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.skill_import_result_interface import (
    SkillImportResultInterface,
)
from engineering_influence.models.skill import Skill


@dataclass(frozen=True, slots=True)
class SkillImportResult(SkillImportResultInterface):
    """The skill that was written, where, which sections it holds, and what was set aside.

    ``ignored`` are frontmatter keys that were read and not used; ``description_shortened`` says the
    description was cut to fit its limit.
    """

    skill: Skill
    path: str
    sections: tuple[str, ...]
    ignored: tuple[str, ...]
    description_shortened: bool

    def __post_init__(self) -> None:
        if not self.path.strip() or not self.sections:
            raise ValueError("an import wrote a file and used at least one section")
