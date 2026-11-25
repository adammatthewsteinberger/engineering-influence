# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Sha256FileHasher: the hash of what a path really holds, and nothing for what is not a file."""

import hashlib
import os
from pathlib import Path

import pytest

from engineering_influence.infrastructure.tools.sha256_file_hasher import Sha256FileHasher
from engineering_influence.interfaces.file_hasher_interface import FileHasherInterface


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_it_is_a_file_hasher() -> None:
    assert isinstance(Sha256FileHasher(), FileHasherInterface)


def test_a_file_is_hashed_by_its_contents(tmp_path: Path) -> None:
    path = tmp_path / "server.js"
    path.write_bytes(b"console.log('hi')\n")
    assert Sha256FileHasher().digest(str(path)) == sha(b"console.log('hi')\n")


def test_an_empty_file_has_the_hash_of_nothing(tmp_path: Path) -> None:
    path = tmp_path / "empty"
    path.write_bytes(b"")
    assert Sha256FileHasher().digest(str(path)) == sha(b"")


def test_a_file_larger_than_one_block_is_hashed_whole(tmp_path: Path) -> None:
    data = os.urandom(Sha256FileHasher.BLOCK * 2 + 123)
    path = tmp_path / "big"
    path.write_bytes(data)
    assert Sha256FileHasher().digest(str(path)) == sha(data)


def test_a_file_exactly_one_block_long_is_hashed_whole(tmp_path: Path) -> None:
    data = os.urandom(Sha256FileHasher.BLOCK)
    path = tmp_path / "one"
    path.write_bytes(data)
    assert Sha256FileHasher().digest(str(path)) == sha(data)


def test_a_symlink_is_hashed_by_what_it_points_at_and_repointing_it_changes_the_hash(
    tmp_path: Path,
) -> None:
    (tmp_path / "one").write_bytes(b"one")
    (tmp_path / "two").write_bytes(b"two")
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "one")
    assert Sha256FileHasher().digest(str(link)) == sha(b"one")
    link.unlink()
    link.symlink_to(tmp_path / "two")
    assert Sha256FileHasher().digest(str(link)) == sha(b"two")


@pytest.mark.parametrize("kind", ["missing", "directory", "dangling link", "link to directory"])
def test_what_is_not_a_regular_file_has_no_hash(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "thing"
    if kind == "directory":
        target.mkdir()
    elif kind == "dangling link":
        target.symlink_to(tmp_path / "nowhere")
    elif kind == "link to directory":
        (tmp_path / "dir").mkdir()
        target.symlink_to(tmp_path / "dir")
    assert Sha256FileHasher().digest(str(target)) is None


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read anything")
def test_a_file_that_cannot_be_read_has_no_hash(tmp_path: Path) -> None:
    path = tmp_path / "secret"
    path.write_bytes(b"x")
    path.chmod(0)
    try:
        assert Sha256FileHasher().digest(str(path)) is None
    finally:
        path.chmod(0o600)


@pytest.mark.skipif(not Path("/dev/null").exists(), reason="needs a device file")
def test_a_device_is_not_a_regular_file_so_it_is_never_opened_or_hashed() -> None:
    assert Sha256FileHasher().digest("/dev/null") is None
