# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes a plugin as a bundle file."""

from engineering_influence.infrastructure.skills.toml_skill_writer import TomlSkillWriter
from engineering_influence.interfaces.plugin_writer_interface import PluginWriterInterface
from engineering_influence.models.plugin import Plugin


class TomlPluginWriter(PluginWriterInterface):
    """The layout ``TomlPluginParser`` reads, with every text quoted the way the skill writer quotes it.

    Servers come first and skills after, each in name order, so the bytes (and their hash) are the same on every run.
    """

    def render(self, plugin: Plugin) -> bytes:
        """The bundle's bytes, which the plugin parser reads back as this plugin."""
        quote = TomlSkillWriter.quote
        lines = [f"name = {quote(plugin.name)}", f"version = {plugin.version}"]
        if plugin.description:
            lines.append(f"description = {quote(plugin.description)}")
        for server in plugin.servers:
            lines += ["", "[[server]]", f"name = {quote(server.name)}"]
            if server.url:
                lines.append(f"url = {quote(server.url)}")
                if server.bearer_env:
                    lines.append(f"bearer_env = {quote(server.bearer_env)}")
                continue
            lines.append("command = [" + ", ".join(quote(part) for part in server.command) + "]")
            if server.env:
                lines.append("env = [" + ", ".join(quote(name) for name in server.env) + "]")
        for skill in plugin.skills:
            lines += ["", "[[skill]]", f"name = {quote(skill.name)}", f"version = {skill.version}"]
            if skill.description:
                lines.append(f"description = {quote(skill.description)}")
            if skill.parts:
                lines += ["", "[skill.parts]"]
                lines += [f"{stage} = {quote(text)}" for stage, text in skill.parts]
            if skill.sections:
                lines += ["", "[skill.reference]"]
                lines += [f"{quote(title)} = {quote(text)}" for title, text in skill.sections]
        return ("\n".join(lines) + "\n").encode("utf-8")
