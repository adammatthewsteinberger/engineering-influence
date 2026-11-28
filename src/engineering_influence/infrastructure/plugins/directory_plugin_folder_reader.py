# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a Claude Code plugin folder."""

import json
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.plugin_folder_reader_interface import (
    PluginFolderReaderInterface,
)
from engineering_influence.interfaces.skill_source_interface import SkillSourceInterface
from engineering_influence.models.plugin_folder import PluginFolder


class DirectoryPluginFolderReader(PluginFolderReaderInterface):
    """Reads ``.claude-plugin/plugin.json``, ``.mcp.json`` and ``skills/*/SKILL.md``, and lists what else is there.

    Only those files are opened. A link is never followed, a JSON file larger than 256 KiB is refused,
    and nothing in the folder is run: not a hook, not a script, not a command. A skill that cannot be read is set
    aside with the reason and does not stop the rest. What the plugin says is untrusted data from here on.
    """

    MAX_JSON_BYTES = 256 * 1024
    MAX_SKILL_FOLDERS = 64
    NOT_IMPORTED = ("agents", "commands", "hooks", "output-styles", "monitors", ".lsp.json")

    def __init__(self, skills: SkillSourceInterface) -> None:
        """Remember the reader that parses a plugin's skills."""
        self._skills = skills

    def read(self, path: Path) -> PluginFolder:
        """The folder's manifest, servers and skills."""
        if path.is_symlink() or not path.is_dir():
            raise self._invalid(f"{path} is not a plugin folder")
        manifest = self._json(path / ".claude-plugin" / "plugin.json")
        set_aside: list[str] = []
        servers = self._servers(path, manifest, set_aside)
        name = manifest.get("name")
        description = manifest.get("description")
        skills = self._skill_texts(path, set_aside)
        for entry in self.NOT_IMPORTED:
            if (path / entry).exists() or (path / entry).is_symlink():
                set_aside.append(f"{entry}: a bundle here grants nothing and runs nothing")
        return PluginFolder(
            name=name if isinstance(name, str) and name.strip() else path.resolve().name,
            description=description if isinstance(description, str) else "",
            servers=servers,
            skills=skills,
            set_aside=tuple(set_aside),
        )

    def _servers(
        self, path: Path, manifest: dict[str, Any], set_aside: list[str]
    ) -> dict[str, Any]:
        found = self._json(path / ".mcp.json")
        table = found.get("mcpServers", found)
        if not isinstance(table, dict) or any(not isinstance(v, dict) for v in table.values()):
            raise self._invalid(".mcp.json is a table of servers, each a table")
        inline = manifest.get("mcpServers")
        if inline is not None and not table:
            if isinstance(inline, dict) and all(isinstance(v, dict) for v in inline.values()):
                return dict(inline)
            set_aside.append("mcpServers in plugin.json: only a table of servers is read")
        return dict(table)

    def _skill_texts(self, path: Path, set_aside: list[str]) -> tuple[tuple[str, str], ...]:
        root = path / "skills"
        if root.is_symlink() or not root.is_dir():
            return ()
        folders = sorted(
            entry for entry in root.iterdir() if not entry.is_symlink() and entry.is_dir()
        )
        if len(folders) > self.MAX_SKILL_FOLDERS:
            set_aside.append(f"skills: only the first {self.MAX_SKILL_FOLDERS} folders are read")
        texts = []
        for folder in folders[: self.MAX_SKILL_FOLDERS]:
            if not (folder / "SKILL.md").is_file() or (folder / "SKILL.md").is_symlink():
                set_aside.append(f"skills/{folder.name}: it has no SKILL.md file")
                continue
            try:
                texts.append((folder.name, self._skills.read(folder)))
            except ApplicationError as error:
                set_aside.append(f"skills/{folder.name}: {error.message}")
        return tuple(texts)

    def _json(self, path: Path) -> dict[str, Any]:
        if path.is_symlink() or not path.exists():
            if path.is_symlink():
                raise self._invalid(f"{path.name} is a link, and links are not followed")
            return {}
        if not path.is_file() or path.stat().st_size > self.MAX_JSON_BYTES:
            raise self._invalid(f"{path.name} is not a file of at most {self.MAX_JSON_BYTES} bytes")
        try:
            data = json.loads(path.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError) as error:
            raise self._invalid(f"{path.name} is not valid JSON text") from error
        if not isinstance(data, dict):
            raise self._invalid(f"{path.name} is a JSON object")
        return data

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(code="PLUGIN_FOLDER_INVALID", message=why, http_status=422)
