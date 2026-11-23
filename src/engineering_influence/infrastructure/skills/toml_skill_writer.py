# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes a skill as a skill file."""

from engineering_influence.interfaces.skill_writer_interface import SkillWriterInterface
from engineering_influence.models.skill import Skill


class TomlSkillWriter(SkillWriterInterface):
    """The layout ``TomlSkillParser`` reads, written the same way every time.

    Every text is a TOML basic string with quotes, backslashes and control characters escaped, so
    what is written reads back as exactly the text that was given, and the hash of the bytes is the
    same on every run.
    """

    def render(self, skill: Skill) -> bytes:
        """The skill file's bytes, which the skill parser reads back as this skill."""
        lines = [f"name = {self._quote(skill.name)}", f"version = {skill.version}"]
        if skill.description:
            lines.append(f"description = {self._quote(skill.description)}")
        if skill.parts:
            lines += ["", "[parts]"]
            lines += [f"{stage} = {self._quote(text)}" for stage, text in skill.parts]
        if skill.sections:
            lines += ["", "[reference]"]
            lines += [
                f"{self._quote(title)} = {self._quote(text)}" for title, text in skill.sections
            ]
        return ("\n".join(lines) + "\n").encode("utf-8")

    @staticmethod
    def _quote(text: str) -> str:
        """A TOML basic string: quotes and backslashes escaped, control characters as \\u escapes."""
        out = []
        for char in text:
            if char in '"\\':
                out.append("\\" + char)
            elif ord(char) < 0x20 or ord(char) == 0x7F:
                out.append(f"\\u{ord(char):04x}")
            else:
                out.append(char)
        return '"' + "".join(out) + '"'
