# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""DirectoryPluginFolderReader opens three kinds of file, follows no link, and says what it set aside."""

import json
import os
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.directory_plugin_folder_reader import (
    DirectoryPluginFolderReader,
)
from engineering_influence.infrastructure.skills.file_skill_source import FileSkillSource
from engineering_influence.interfaces.plugin_folder_reader_interface import (
    PluginFolderReaderInterface,
)

READER = DirectoryPluginFolderReader(FileSkillSource())


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def skill(root: Path, name: str, text: str = "---\nname: x\ndescription: y\n---\nbody") -> None:
    (root / "skills" / name).mkdir(parents=True)
    (root / "skills" / name / "SKILL.md").write_text(text, encoding="utf-8")


def refused(path: Path) -> str:
    with pytest.raises(ApplicationError) as error:
        READER.read(path)
    assert (error.value.code, error.value.http_status) == ("PLUGIN_FOLDER_INVALID", 422)
    return error.value.message


def test_it_is_a_reader() -> None:
    assert isinstance(READER, PluginFolderReaderInterface)


def test_a_folder_with_a_manifest_servers_and_skills_is_read(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".claude-plugin" / "plugin.json", {"name": "Pack", "description": "Does things"}
    )
    write_json(tmp_path / ".mcp.json", {"mcpServers": {"s": {"command": "/bin/x"}}})
    skill(tmp_path, "b")
    skill(tmp_path, "a")
    made = READER.read(tmp_path)
    assert (made.name, made.description) == ("Pack", "Does things")
    assert dict(made.servers) == {"s": {"command": "/bin/x"}}
    assert [label for label, _ in made.skills] == ["a", "b"]
    assert made.set_aside == ()


def test_a_flat_mcp_file_is_read_the_same_way(tmp_path: Path) -> None:
    write_json(tmp_path / ".mcp.json", {"s": {"url": "https://x.example/mcp"}})
    assert dict(READER.read(tmp_path).servers) == {"s": {"url": "https://x.example/mcp"}}


def test_with_no_manifest_the_folders_name_is_the_name_and_a_blank_name_is_ignored(
    tmp_path: Path,
) -> None:
    plain = tmp_path / "my-plugin"
    plain.mkdir()
    assert READER.read(plain).name == "my-plugin" and READER.read(plain).description == ""
    write_json(plain / ".claude-plugin" / "plugin.json", {"name": " ", "description": 3})
    assert READER.read(plain).name == "my-plugin" and READER.read(plain).description == ""


def test_servers_written_inside_the_manifest_are_read_when_there_is_no_mcp_file(
    tmp_path: Path,
) -> None:
    write_json(
        tmp_path / ".claude-plugin" / "plugin.json", {"mcpServers": {"s": {"command": "/x"}}}
    )
    made = READER.read(tmp_path)
    assert dict(made.servers) == {"s": {"command": "/x"}} and made.set_aside == ()


def test_the_mcp_file_wins_over_servers_written_in_the_manifest(tmp_path: Path) -> None:
    write_json(
        tmp_path / ".claude-plugin" / "plugin.json", {"mcpServers": {"a": {"command": "/x"}}}
    )
    write_json(tmp_path / ".mcp.json", {"mcpServers": {"b": {"command": "/y"}}})
    assert list(READER.read(tmp_path).servers) == ["b"]


@pytest.mark.parametrize("inline", ["./mcp.json", ["./a.json"], {"s": "text"}])
def test_servers_in_the_manifest_that_are_not_a_table_of_tables_are_set_aside(
    tmp_path: Path, inline: object
) -> None:
    write_json(tmp_path / ".claude-plugin" / "plugin.json", {"mcpServers": inline})
    made = READER.read(tmp_path)
    assert dict(made.servers) == {}
    assert made.set_aside == ("mcpServers in plugin.json: only a table of servers is read",)


def test_what_a_bundle_cannot_hold_is_listed_and_never_opened(tmp_path: Path) -> None:
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "hooks.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "commands").mkdir()
    (tmp_path / ".lsp.json").write_text("{}", encoding="utf-8")
    made = READER.read(tmp_path)
    assert [line.split(":")[0] for line in made.set_aside] == ["commands", "hooks", ".lsp.json"]
    assert all("grants nothing and runs nothing" in line for line in made.set_aside)


def test_a_link_for_something_a_bundle_cannot_hold_is_listed_too(tmp_path: Path) -> None:
    os.symlink(tmp_path / "nowhere", tmp_path / "agents")
    assert [line.split(":")[0] for line in READER.read(tmp_path).set_aside] == ["agents"]


def test_a_skill_folder_without_a_skill_md_or_with_a_bad_one_is_set_aside_with_the_reason(
    tmp_path: Path,
) -> None:
    (tmp_path / "skills" / "empty").mkdir(parents=True)
    skill(tmp_path, "fine")
    (tmp_path / "skills" / "big").mkdir()
    (tmp_path / "skills" / "big" / "SKILL.md").write_bytes(b"x" * (256 * 1024 + 1))
    (tmp_path / "skills" / "linked").mkdir()
    os.symlink(
        tmp_path / "skills" / "fine" / "SKILL.md", tmp_path / "skills" / "linked" / "SKILL.md"
    )
    (tmp_path / "skills" / "loose.md").write_text("not a folder", encoding="utf-8")
    made = READER.read(tmp_path)
    assert [label for label, _ in made.skills] == ["fine"]
    assert made.set_aside[0] == "skills/big: " + (
        f"{tmp_path / 'skills' / 'big' / 'SKILL.md'} is larger than 262144 bytes"
    )
    assert "skills/empty: it has no SKILL.md file" in made.set_aside
    assert "skills/linked: it has no SKILL.md file" in made.set_aside
    assert len(made.set_aside) == 3


def test_only_the_first_sixty_four_skill_folders_are_read(tmp_path: Path) -> None:
    for number in range(65):
        skill(tmp_path, f"s{number:02d}")
    made = READER.read(tmp_path)
    assert len(made.skills) == 64 and made.skills[-1][0] == "s63"
    assert made.set_aside == ("skills: only the first 64 folders are read",)


def test_a_skills_link_is_not_followed(tmp_path: Path) -> None:
    other = tmp_path / "other"
    skill(other, "a")
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    os.symlink(other / "skills", plugin / "skills")
    assert READER.read(plugin).skills == ()


def test_a_path_that_is_not_a_folder_or_is_a_link_is_refused(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("x", encoding="utf-8")
    assert "is not a plugin folder" in refused(tmp_path / "file")
    assert "is not a plugin folder" in refused(tmp_path / "missing")
    real = tmp_path / "real"
    real.mkdir()
    os.symlink(real, tmp_path / "link")
    assert "is not a plugin folder" in refused(tmp_path / "link")


def test_a_json_file_that_is_a_link_a_folder_too_big_or_not_json_is_refused(
    tmp_path: Path,
) -> None:
    root = tmp_path / "p"
    root.mkdir()
    real = tmp_path / "real.json"
    real.write_text("{}", encoding="utf-8")
    os.symlink(real, root / ".mcp.json")
    assert refused(root) == ".mcp.json is a link, and links are not followed"
    (root / ".mcp.json").unlink()
    (root / ".mcp.json").mkdir()
    assert "is not a file of at most 262144 bytes" in refused(root)
    (root / ".mcp.json").rmdir()
    (root / ".mcp.json").write_bytes(b" " * (256 * 1024 + 1))
    assert "is not a file of at most 262144 bytes" in refused(root)
    (root / ".mcp.json").write_text("{nope", encoding="utf-8")
    assert refused(root) == ".mcp.json is not valid JSON text"
    (root / ".mcp.json").write_bytes(b"\xff\xfe")
    assert refused(root) == ".mcp.json is not valid JSON text"
    (root / ".mcp.json").write_text("[" * 100_000, encoding="utf-8")
    assert refused(root) == ".mcp.json is not valid JSON text"


def test_json_that_is_not_an_object_or_servers_that_are_not_tables_are_refused(
    tmp_path: Path,
) -> None:
    write_json(tmp_path / ".mcp.json", [1])
    assert refused(tmp_path) == ".mcp.json is a JSON object"
    write_json(tmp_path / ".mcp.json", {"mcpServers": ["a"]})
    assert refused(tmp_path) == ".mcp.json is a table of servers, each a table"
    write_json(tmp_path / ".mcp.json", {"mcpServers": {"a": "x"}})
    assert refused(tmp_path) == ".mcp.json is a table of servers, each a table"


def test_exactly_sixty_four_skill_folders_are_read_without_a_note(tmp_path: Path) -> None:
    for number in range(64):
        skill(tmp_path, f"s{number:02d}")
    made = READER.read(tmp_path)
    assert len(made.skills) == 64 and made.set_aside == ()


def test_a_skill_folder_that_is_a_link_is_not_followed(tmp_path: Path) -> None:
    other = tmp_path / "other"
    skill(other, "real")
    plugin = tmp_path / "plugin"
    skill(plugin, "fine")
    os.symlink(other / "skills" / "real", plugin / "skills" / "linked")
    made = READER.read(plugin)
    assert [label for label, _ in made.skills] == ["fine"] and made.set_aside == ()


def test_a_json_file_of_exactly_the_limit_is_read(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_bytes(b"{}" + b" " * (256 * 1024 - 2))
    assert dict(READER.read(tmp_path).servers) == {}
