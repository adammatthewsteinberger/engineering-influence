# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The release helper that gives each develop build a version of its own."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from packaging.version import Version

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "stamp_dev_version.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("stamp_dev_version", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load()
STAMPER = MODULE.DevVersionStamper()
CORE = 'ABOVE\n__version__ = "{v}"\n__all__ = ["x"]\n'


def write(tmp_path: Path, name: str, version: str = "0.1.0a2", text: str = CORE) -> Path:
    path = tmp_path / name
    path.write_text(text.format(v=version), encoding="utf-8")
    return path


def test_the_version_line_gets_the_dev_suffix_and_nothing_else_changes(tmp_path: Path) -> None:
    path = write(tmp_path, "core.py")

    assert STAMPER.stamp_all([path], "123") == "0.1.0a2.dev123"
    assert path.read_text(encoding="utf-8") == CORE.format(v="0.1.0a2.dev123")


def test_every_file_gets_the_same_version(tmp_path: Path) -> None:
    core, sdk = write(tmp_path, "core.py"), write(tmp_path, "sdk.py")

    assert STAMPER.stamp_all([core, sdk], "7") == "0.1.0a2.dev7"
    assert core.read_text(encoding="utf-8") == sdk.read_text(encoding="utf-8")


@pytest.mark.parametrize("version", ["0.1.0", "1.20.3", "0.1.0a2", "0.1.0b11", "2.0.0rc1"])
def test_a_plain_release_version_is_stamped(tmp_path: Path, version: str) -> None:
    assert STAMPER.stamp_all([write(tmp_path, "v.py", version)], "1") == f"{version}.dev1"


@pytest.mark.parametrize(
    "version", ["0.1.0a2.dev3", "0.1", "0.1.0.post1", "v0.1.0", "0.1.0+local", "x"]
)
def test_anything_else_is_refused(tmp_path: Path, version: str) -> None:
    path = write(tmp_path, "v.py", version)

    with pytest.raises(ValueError, match="not a plain release version"):
        STAMPER.stamp_all([path], "1")
    assert path.read_text(encoding="utf-8") == CORE.format(v=version)


@pytest.mark.parametrize("build", ["", "abc", "1.2", "-1", " 1", "1 ", "١٢", "²", "1" * 19])
def test_a_build_number_is_plain_ascii_digits(tmp_path: Path, build: str) -> None:
    path = write(tmp_path, "v.py")

    with pytest.raises(ValueError, match="digits only"):
        STAMPER.stamp_all([path], build)
    assert path.read_text(encoding="utf-8") == CORE.format(v="0.1.0a2")


def test_leading_zeros_are_dropped_so_the_version_is_the_one_pip_will_read(tmp_path: Path) -> None:
    assert STAMPER.stamp_all([write(tmp_path, "v.py")], "007") == "0.1.0a2.dev7"
    assert STAMPER.stamp_all([write(tmp_path, "w.py")], "0") == "0.1.0a2.dev0"
    assert STAMPER.stamp_all([write(tmp_path, "x.py")], "1" * 18) == f"0.1.0a2.dev{'1' * 18}"


def test_a_file_needs_exactly_one_version_line(tmp_path: Path) -> None:
    for text in (
        "no version here\n",
        '__version__ = "0.1.0"\n__version__ = "0.1.0"\n',
        ' __version__ = "0.1.0"\n',
    ):
        path = tmp_path / "v.py"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError, match="exactly one __version__ line"):
            STAMPER.stamp_all([path], "1")


def test_files_that_disagree_are_all_left_alone(tmp_path: Path) -> None:
    core, sdk = write(tmp_path, "core.py", "0.1.0a2"), write(tmp_path, "sdk.py", "0.1.0a1")

    with pytest.raises(ValueError, match="different versions"):
        STAMPER.stamp_all([core, sdk], "1")
    assert core.read_text(encoding="utf-8") == CORE.format(v="0.1.0a2")
    assert sdk.read_text(encoding="utf-8") == CORE.format(v="0.1.0a1")


def test_a_second_bad_file_stops_the_first_from_being_stamped(tmp_path: Path) -> None:
    good, bad = write(tmp_path, "good.py"), write(tmp_path, "bad.py", "0.1.0a2.dev1")

    with pytest.raises(ValueError, match="not a plain release version"):
        STAMPER.stamp_all([good, bad], "5")
    assert good.read_text(encoding="utf-8") == CORE.format(v="0.1.0a2")


def test_no_files_is_an_error() -> None:
    with pytest.raises(ValueError, match="no file to stamp"):
        STAMPER.stamp_all([], "1")


def test_a_dev_build_sorts_before_its_release_and_in_build_order(tmp_path: Path) -> None:
    five = Version(STAMPER.stamp_all([write(tmp_path, "a.py")], "5"))
    twelve = Version(STAMPER.stamp_all([write(tmp_path, "b.py")], "12"))

    assert five < twelve < Version("0.1.0a2")
    assert five.is_devrelease and five.is_prerelease


def test_the_command_prints_the_stamped_version(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, "v.py")

    assert MODULE.main(["42", str(path)]) == 0
    assert capsys.readouterr().out == "0.1.0a2.dev42\n"
    assert "dev42" in path.read_text(encoding="utf-8")


def test_the_command_reports_a_problem_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, "v.py", "0.1.0a2.dev1")

    assert MODULE.main(["1", str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ")


def test_the_command_reports_a_missing_file_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert MODULE.main(["1", str(tmp_path / "missing.py")]) == 1
    assert capsys.readouterr().err.startswith("error: ")
