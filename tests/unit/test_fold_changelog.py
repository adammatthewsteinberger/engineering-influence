"""The release helper that folds changelog fragments into a version section."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fold_changelog.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fold_changelog", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load()
CHANGELOG = "# Changelog\n\n## Unreleased\n\n- kept from before\n\n## 0.1.0a1\n\n- first\n"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "changelog.d").mkdir()
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    (tmp_path / "changelog.d" / "README.md").write_text("how to\n", encoding="utf-8")
    return tmp_path


def fragment(root: Path, name: str, text: str) -> None:
    (root / "changelog.d" / name).write_text(text, encoding="utf-8")


def test_fragments_become_bullets_in_file_name_order_and_are_deleted(root: Path) -> None:
    fragment(root, "b-second.md", "Second change.\n")
    fragment(root, "a-first.md", "First change.\n")
    assert MODULE.main(["0.1.0a2", "--root", str(root)]) == 0
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text == (
        "# Changelog\n\n## Unreleased\n\n## 0.1.0a2\n\n"
        "- First change.\n- Second change.\n- kept from before\n\n## 0.1.0a1\n\n- first\n"
    )
    assert [p.name for p in (root / "changelog.d").iterdir()] == ["README.md"]


def test_with_no_fragments_the_unreleased_bullets_still_get_the_version(root: Path) -> None:
    assert MODULE.ChangelogFolder(root).fold("0.1.0a2") == 0
    assert "## 0.1.0a2\n\n- kept from before\n" in (root / "CHANGELOG.md").read_text("utf-8")


def test_an_empty_unreleased_section_gets_only_the_fragments(root: Path) -> None:
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n## 0.1.0a1\n\n- first\n", encoding="utf-8"
    )
    fragment(root, "x.md", "Only change.")
    MODULE.ChangelogFolder(root).fold("0.1.0a2")
    assert "## 0.1.0a2\n\n- Only change.\n\n## 0.1.0a1" in (root / "CHANGELOG.md").read_text(
        "utf-8"
    )


@pytest.mark.parametrize("version", ["1.0", "v1.0.0", "1.0.0-rc1", ""])
def test_a_malformed_version_is_refused(root: Path, version: str) -> None:
    assert MODULE.main([version, "--root", str(root)]) == 1


def test_a_version_that_already_has_a_section_is_refused(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fragment(root, "x.md", "A change.")
    assert MODULE.main(["0.1.0a1", "--root", str(root)]) == 1
    assert "already has a section" in capsys.readouterr().err
    assert (root / "changelog.d" / "x.md").exists()


def test_a_changelog_without_an_unreleased_section_is_refused(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    assert MODULE.main(["0.1.0a2", "--root", str(root)]) == 1
    assert "no '## Unreleased'" in capsys.readouterr().err
