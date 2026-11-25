"""The shared lock file helpers: blocks are written exactly, and a link at the temporary name is never written through."""

import os
from pathlib import Path

from engineering_influence.infrastructure.toml_lock_file import TomlLockFile


def test_blocks_are_written_one_blank_line_apart(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    TomlLockFile.write(path, ["a = 1\n", "b = 2\n"])
    assert path.read_text(encoding="utf-8") == "a = 1\n\nb = 2\n"


def test_a_link_planted_at_the_temporary_name_is_not_written_through(tmp_path: Path) -> None:
    target = tmp_path / "outside.txt"
    target.write_text("keep", encoding="utf-8")
    path = tmp_path / "lock.toml"
    os.symlink(target, tmp_path / ".lock.toml.tmp")
    TomlLockFile.write(path, ["x = 1\n"])
    assert target.read_text(encoding="utf-8") == "keep"
    assert path.read_text(encoding="utf-8") == "x = 1\n"
