# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TempProjectManuscriptAuditor: the book is laid out in a scratch folder, audited there, and the folder removed."""

from pathlib import Path
from typing import Any

import pytest

from engineering_influence.infrastructure.audit.temp_project_manuscript_auditor import (
    TempProjectManuscriptAuditor,
)
from engineering_influence.interfaces.manuscript_auditor_interface import (
    ManuscriptAuditorInterface,
)
from engineering_influence.interfaces.publish_pipeline_interface import PublishPipelineInterface


class Pipeline(PublishPipelineInterface):
    """Writes reports where the real pipeline does and answers with a scripted result."""

    def __init__(
        self, root: Path, result: dict[str, Any], passed: bool, reports: tuple[str, ...]
    ) -> None:
        self.root = root
        self.result = result
        self.passed = passed
        self.reports = reports
        self.seen: list[tuple[str, dict[str, Any], dict[str, bytes]]] = []

    def publish(
        self,
        slug: str,
        *,
        dpi: int = 90,
        audit_only: bool = False,
        no_render: bool = False,
        report_path: Path | None = None,
        strict_release: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        files = {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        }
        self.seen.append((slug, {"audit_only": audit_only, "strict": strict_release}, files))
        release = self.root / "build" / slug / "release"
        release.mkdir(parents=True)
        for name in self.reports:
            (release / name).write_bytes(f"report {name}".encode())
        return self.result, self.passed


def result(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "status": "pass",
        "manuscript_audit": {
            "issues": [],
            "warnings": [{"code": "short", "message": "chapter 2 is short"}],
        },
        "release_readiness": {
            "findings": [{"severity": "warning", "code": "price", "message": "no price"}]
        },
    }
    return {**base, **changes}


def messy() -> dict[str, Any]:
    return result(
        status="fail",
        manuscript_audit={
            "issues": [{"code": "dash", "message": "page 3"}],
            "warnings": [{"code": "short", "message": "chapter 2 is short"}],
        },
        release_readiness={
            "findings": [
                {"severity": "error", "code": "missing-author", "message": "no author"},
                {"severity": "warning", "code": "price", "message": "no price"},
            ]
        },
    )


class Harness:
    def __init__(
        self,
        scripted: dict[str, Any],
        passed: bool = True,
        reports: tuple[str, ...] = TempProjectManuscriptAuditor.REPORTS,
    ) -> None:
        self.pipelines: list[Pipeline] = []
        self.roots: list[Path] = []

        def make(root: Path) -> PublishPipelineInterface:
            self.roots.append(root)
            pipeline = Pipeline(root, scripted, passed, reports)
            self.pipelines.append(pipeline)
            return pipeline

        self.auditor = TempProjectManuscriptAuditor(make)


FILES = {"books/hive.toml": b"title = 'x'", "src/chapter_01.md": b"# One\n"}


def test_it_is_a_manuscript_auditor() -> None:
    assert isinstance(Harness(result()).auditor, ManuscriptAuditorInterface)


def test_the_files_are_laid_out_as_a_project_and_the_audit_gates_alone_are_run() -> None:
    harness = Harness(result())
    harness.auditor.audit(FILES, "hive")
    slug, options, files = harness.pipelines[0].seen[0]
    assert slug == "hive"
    assert options == {"audit_only": True, "strict": False}
    assert files == FILES


def test_the_reports_are_read_back_by_name_and_the_scratch_folder_is_gone() -> None:
    harness = Harness(result())
    audit = harness.auditor.audit(FILES, "hive")
    assert audit.files == (
        ("manuscript-audit.json", b"report manuscript-audit.json"),
        ("release-readiness.json", b"report release-readiness.json"),
        ("publication-report.json", b"report publication-report.json"),
    )
    assert not harness.roots[0].exists()


def test_a_report_the_pipeline_did_not_write_is_left_out() -> None:
    audit = Harness(result(), reports=("release-readiness.json",)).auditor.audit(FILES, "hive")
    assert [name for name, _ in audit.files] == ["release-readiness.json"]


def test_errors_are_the_audit_issues_and_the_release_errors_and_warnings_are_the_rest() -> None:
    audit = Harness(messy(), passed=False, reports=()).auditor.audit(FILES, "hive")
    assert audit.errors == ("dash: page 3", "missing-author: no author")
    assert audit.warnings == ("short: chapter 2 is short", "price: no price")
    assert (audit.passed, audit.status) == (False, "fail")


def test_the_status_and_the_verdict_come_from_the_pipeline() -> None:
    audit = Harness(result(status="fail"), passed=False).auditor.audit(FILES, "hive")
    assert (audit.passed, audit.status, audit.errors) == (False, "fail", ())
    clean = Harness(result()).auditor.audit(FILES, "hive")
    assert (clean.passed, clean.status) == (True, "pass")


@pytest.mark.parametrize("name", ["../escape.md", "src/../../escape.md", "/etc/passwd", ".", ""])
def test_a_file_that_would_leave_the_project_is_refused_before_anything_runs(name: str) -> None:
    harness = Harness(result())
    with pytest.raises(ValueError, match="would leave the project"):
        harness.auditor.audit({**FILES, name: b"x"}, "hive")
    assert harness.pipelines == [] or harness.pipelines[0].seen == []


def test_the_scratch_folder_is_removed_even_when_the_pipeline_fails() -> None:
    harness = Harness(result())

    def boom(root: Path) -> PublishPipelineInterface:
        harness.roots.append(root)
        raise RuntimeError("the pipeline broke")

    with pytest.raises(RuntimeError):
        TempProjectManuscriptAuditor(boom).audit(FILES, "hive")
    assert not harness.roots[0].exists()
