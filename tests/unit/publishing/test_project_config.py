"""Project layout and config, the audit text renderings, and plugin roots."""

import sys
from pathlib import Path

import pytest

from engineering_influence.publishing.audit_report import AuditReport
from engineering_influence.publishing.audit_report_text import AuditReportText
from engineering_influence.publishing.covers.cover_plugin import CoverPlugin
from engineering_influence.publishing.covers.cover_plugin_loader import CoverPluginLoader
from engineering_influence.publishing.covers.painter_registry import PainterRegistry
from engineering_influence.publishing.issue import Issue
from engineering_influence.publishing.project_config import ProjectConfig
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.readiness_report import ReadinessReport


def test_layout_directories_can_be_renamed(tmp_path: Path) -> None:
    layout = ProjectLayout(tmp_path, books_dir="configs", output_dir="out", build_dir="work")
    assert (layout.books, layout.output, layout.build) == (
        tmp_path / "configs",
        tmp_path / "out",
        tmp_path / "work",
    )


def test_config_defaults_without_a_file(tmp_path: Path) -> None:
    config = ProjectConfig.load(tmp_path)
    assert config.layout() == ProjectLayout(tmp_path.resolve())
    assert config.cover_plugin is None and config.font_dirs() == [
        tmp_path.resolve() / "covers" / "fonts"
    ]


def test_config_reads_every_documented_key(tmp_path: Path) -> None:
    (tmp_path / "engineering-influence.toml").write_text(
        '[books]\nconfig_dir = "configs"\n[artifacts]\ndirectory = "out"\n[build]\ndirectory = "work"\n'
        '[covers]\nplugin = "my.mod:Plugin"\nfonts = "assets/fonts"\n[tool]\npackage = "x"\n',
        encoding="utf-8",
    )
    config = ProjectConfig.load(tmp_path)
    assert config.layout() == ProjectLayout(tmp_path.resolve(), "configs", "out", "work")
    assert config.cover_plugin == "my.mod:Plugin"
    assert config.font_dirs() == [tmp_path.resolve() / "assets" / "fonts"]


def test_activate_makes_the_project_importable_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "path", list(sys.path))
    config = ProjectConfig.load(tmp_path)
    config.activate()
    config.activate()
    assert sys.path.count(str(tmp_path.resolve())) == 1 and sys.path[0] == str(tmp_path.resolve())


def test_manuscript_report_text() -> None:
    report = AuditReport(
        1, "demo", "c", "s", counts={"listed_words": 1234, "chapter_count": 2, "back_count": 1}
    )
    report.add(Issue("error", "a-code", "with line", "src/a.md", 7))
    report.add(Issue("error", "b-code", "path only", "src/b.md"))
    report.add(Issue("error", "c-code", "no path"))
    report.add(Issue("warning", "w-code", "just a warning"))
    assert AuditReportText().manuscript(report).splitlines() == [
        "[demo] 1,234 listed words, 2 chapters, 1 back-matter entries",
        "ERROR [a-code] src/a.md:7: with line",
        "ERROR [b-code] src/b.md: path only",
        "ERROR [c-code]: no path",
        "WARNING [w-code]: just a warning",
    ]


def test_manuscript_report_text_for_passing_audits() -> None:
    clean = AuditReport(1, "demo", "c", "s")
    assert AuditReportText().manuscript(clean).splitlines()[-1] == "[demo] manuscript audit passed"
    warned = AuditReport(1, "demo", "c", "s")
    warned.add(Issue("warning", "w", "x"))
    assert (
        AuditReportText().manuscript(warned).splitlines()[-1]
        == "[demo] manuscript audit passed, 1 warning(s)"
    )


def test_release_report_text() -> None:
    report = ReadinessReport(1, "demo", "fail", "demo.toml", None)
    report.add("error", "e", "bad", "demo.toml")
    report.add("warning", "w", "meh")
    assert AuditReportText().release(report).splitlines() == [
        "[demo] release readiness fail; 1 error(s), 1 warning(s)",
        "ERROR [e] bad (demo.toml)",
        "WARNING [w] meh",
    ]


class RootPlugin(CoverPlugin):
    def painters(self) -> dict:
        return {}

    def styles(self) -> dict:
        return {}


def test_plugins_know_their_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert RootPlugin().root == Path.cwd() and RootPlugin(tmp_path).root == tmp_path
    (tmp_path / "rootmod.py").write_text(
        "from tests_root_support import RootPlugin as Plugin\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(sys.modules, "tests_root_support", sys.modules[__name__])
    loader = CoverPluginLoader()
    seen: list[Path] = []
    original = RootPlugin.__init__

    def spy(self: RootPlugin, root: Path | None = None) -> None:
        original(self, root)
        seen.append(self.root)

    monkeypatch.setattr(RootPlugin, "__init__", spy)
    loader.load_reference("rootmod:Plugin", PainterRegistry(), tmp_path)
    loader.load_reference("rootmod:Plugin", PainterRegistry())
    assert seen == [tmp_path, Path.cwd()]
