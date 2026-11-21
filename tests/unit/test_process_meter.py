# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ProcessMeter: reads real processes and real directories."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from engineering_influence.infrastructure.process.process_meter import ProcessMeter

MIB = 2**20


def holder(megabytes: int) -> subprocess.Popen[str]:
    """A child in its own group that holds the memory and then sleeps."""
    code = (
        f"import time; data = b'x' * ({megabytes} * 1024 * 1024); print('up', flush=True); "
        "time.sleep(60)"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", code], stdout=subprocess.PIPE, text=True, start_new_session=True
    )
    assert process.stdout is not None and process.stdout.readline() == "up\n"
    return process


def test_memory_is_the_resident_size_of_the_whole_group() -> None:
    process = holder(200)
    try:
        measured = ProcessMeter().memory_bytes(process.pid)
        assert 200 * MIB < measured < 600 * MIB
    finally:
        process.kill()
        process.wait()
        if process.stdout:
            process.stdout.close()


def test_memory_of_a_group_that_is_gone_is_zero() -> None:
    finished = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    finished.wait()
    assert ProcessMeter().memory_bytes(finished.pid) == 0


def test_memory_counts_only_the_named_group() -> None:
    process = holder(200)
    try:
        assert ProcessMeter().memory_bytes(process.pid + 7919) == 0
    finally:
        process.kill()
        process.wait()
        if process.stdout:
            process.stdout.close()


def test_disk_is_the_total_size_of_the_files_below_the_directory(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"x" * 1000)
    (tmp_path / "deep" / "er").mkdir(parents=True)
    (tmp_path / "deep" / "b.bin").write_bytes(b"x" * 250)
    (tmp_path / "deep" / "er" / "c.bin").write_bytes(b"x" * 25)
    assert ProcessMeter().disk_bytes(tmp_path) == 1275


def test_disk_does_not_follow_symbolic_links(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "huge.bin").write_bytes(b"x" * MIB)
    inside = tmp_path / "inside"
    inside.mkdir()
    (inside / "file.bin").write_bytes(b"x" * 10)
    (inside / "file-link").symlink_to(outside / "huge.bin")
    (inside / "dir-link").symlink_to(outside, target_is_directory=True)
    link_size = os.lstat(inside / "file-link").st_size
    assert ProcessMeter().disk_bytes(inside) == 10 + link_size < MIB


def test_disk_of_a_directory_that_does_not_exist_is_zero(tmp_path: Path) -> None:
    assert ProcessMeter().disk_bytes(tmp_path / "absent") == 0


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read anything")
def test_an_entry_that_cannot_be_read_counts_as_nothing(tmp_path: Path) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "f.bin").write_bytes(b"x" * 10)
    locked.chmod(0o444)  # the names can be listed, but the entries cannot be examined
    try:
        assert ProcessMeter().disk_bytes(locked) == 0
    finally:
        locked.chmod(0o755)


TWO_HOLDERS = """
import subprocess, sys, time
from pathlib import Path
ready = Path(sys.argv[1])
child = "import sys, time; from pathlib import Path; d = b'x' * (200 * 1024 * 1024); Path(sys.argv[1]).write_text('x'); time.sleep(60)"
subprocess.Popen([sys.executable, "-c", child, str(ready)])
data = b"x" * (200 * 1024 * 1024)
while not ready.exists():
    time.sleep(0.05)
print("up", flush=True)
time.sleep(60)
"""


def test_memory_is_summed_over_every_process_in_the_group(tmp_path: Path) -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", TWO_HOLDERS, str(tmp_path / "ready")],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        assert process.stdout is not None and process.stdout.readline() == "up\n"
        assert ProcessMeter().memory_bytes(process.pid) > 350 * MIB
    finally:
        os.killpg(process.pid, 9)
        process.wait()
        if process.stdout:
            process.stdout.close()
