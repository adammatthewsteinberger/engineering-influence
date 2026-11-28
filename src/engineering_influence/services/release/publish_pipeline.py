# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The complete manuscript-to-publication acceptance pipeline.

source audit -> PDF interior -> cover geometry and art -> EPUB -> all-page render -> manifest.

It makes the dependency order explicit and keeps evidence for each step, so a release does not
depend on remembering the sequence, the render commands, or the final inventory by hand.
"""

import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.interfaces.artifact_inventory_interface import (
    ArtifactInventoryInterface,
)
from engineering_influence.interfaces.build_workspace_interface import BuildWorkspaceInterface
from engineering_influence.interfaces.clock_interface import ClockInterface
from engineering_influence.interfaces.epub_zip_check_interface import EpubZipCheckInterface
from engineering_influence.interfaces.git_state_interface import GitStateInterface
from engineering_influence.interfaces.json_report_interface import JsonReportInterface
from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface
from engineering_influence.interfaces.publish_pipeline_interface import PublishPipelineInterface
from engineering_influence.interfaces.render_qa_interface import RenderQaInterface
from engineering_influence.interfaces.step_recorder_interface import StepRecorderInterface
from engineering_influence.interfaces.tool_versions_interface import ToolVersionsInterface
from engineering_influence.models.publishing.path_relativizer import PathRelativizer
from engineering_influence.models.publishing.project_layout import ProjectLayout
from engineering_influence.models.typesetting.trim_size import TrimSize
from engineering_influence.services.publishing.book_auditor import BookAuditor
from engineering_influence.services.publishing.release_auditor import ReleaseAuditor
from engineering_influence.services.release.format_policy import FormatPolicy
from engineering_influence.services.release.page_limit_check import PageLimitCheck
from engineering_influence.services.release.publish_steps import PublishSteps
from engineering_influence.services.release.release_summary import ReleaseSummary


class PublishPipeline(PublishPipelineInterface):
    """Runs a book through every gate and writes publication-report.json."""

    def __init__(
        self,
        layout: ProjectLayout,
        steps: PublishSteps,
        files: ManuscriptSourceInterface,
        pdfs: PdfInspectorInterface,
        qa: RenderQaInterface,
        clock: ClockInterface,
        reports: JsonReportInterface,
        inventory: ArtifactInventoryInterface,
        git: GitStateInterface,
        tools: ToolVersionsInterface,
        epub_zip: EpubZipCheckInterface,
        recorder: StepRecorderInterface,
        workspace: BuildWorkspaceInterface,
    ) -> None:
        """Remember the layout, steps, source files, PDF inspector, render QA and clock the publication runs with."""
        self._layout = layout
        self._steps = steps
        self._files = files
        self._pdfs = pdfs
        self._qa = qa
        self._clock = clock
        self._relativizer = PathRelativizer(layout.root)
        self._json = reports
        self._inventory = inventory
        self._git = git
        self._tools = tools
        self._epub_zip = epub_zip
        self._recorder = recorder
        self._workspace = workspace

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
        """Return (the report, whether every gate passed)."""
        config = self._layout.books / f"{slug}.toml"
        if not self._files.exists(config):
            raise BookBuildError(f"no such book config: {self._relativizer.relative(config)}")
        data = tomllib.loads(self._files.read_text(config))
        formats = FormatPolicy().of(data)
        hardcover = bool(formats["hardcover"])
        hardcover_wrap = TrimSize.for_name(data.get("trim_size")).hardcover
        report_dir = self._layout.build / slug / "release"
        self._workspace.ensure_tree(report_dir)
        release = data.get("release")
        strict = strict_release or (
            isinstance(release, dict) and bool(release.get("required", False))
        )

        audit_report = BookAuditor(self._layout.root, self._files).audit(config)
        release_report = ReleaseAuditor(self._layout.root, self._files, self._pdfs).audit(
            config, strict=strict
        )
        audit_path = report_dir / "manuscript-audit.json"
        release_path = report_dir / "release-readiness.json"
        self._json.write(audit_path, audit_report.as_dict())
        self._json.write(release_path, release_report.as_dict())

        summary = ReleaseSummary().of(release_report, self._relativizer.relative(release_path))
        result = self._initial_result(
            slug, data, formats, config, audit_report, release_report, audit_path, summary
        )
        result_path = report_path or report_dir / "publication-report.json"
        preflight_ok = not audit_report.issues and not release_report.errors
        if not preflight_ok or audit_only:
            result["artifacts"] = self._inventory.artifacts(
                slug, hardcover=hardcover, hardcover_wrap=hardcover_wrap
            )
            result["finished_at"] = self._clock.now().isoformat()
            self._json.write(result_path, result)
            return result, preflight_ok

        hardcover_pdf = self._layout.output / f"{slug}-hardcover.pdf"
        self._run_steps(slug, hardcover, report_dir, result, strict)
        result["artifacts"] = self._inventory.artifacts(
            slug, hardcover=hardcover, hardcover_wrap=hardcover_wrap
        )
        self._check_artifacts(
            result, hardcover, hardcover_pdf, formats["hardcover_max_pages"], slug
        )
        pdf = self._layout.output / f"{slug}.pdf"
        if self._files.exists(pdf):
            self._recheck_release(result, config, pdf, strict, release_path)
        if result["status"] == "pass" and not no_render:
            self._visual_qa(result, slug, pdf, hardcover_pdf, hardcover, dpi)
        elif no_render:
            result["visual_qa"] = {"status": "skipped", "reason": "--no-render"}
        if self._files.exists(pdf):
            result["pdf"] = {"pages": self._pdfs.page_count(pdf)}
        if self._files.exists(hardcover_pdf):
            result["hardcover_pdf"] = {"pages": self._pdfs.page_count(hardcover_pdf)}
        result["finished_at"] = self._clock.now().isoformat()
        self._json.write(result_path, result)
        return result, bool(result["status"] == "pass")

    def _initial_result(
        self,
        slug: str,
        data: dict[str, Any],
        formats: dict[str, Any],
        config: Path,
        audit_report: Any,
        release_report: Any,
        audit_path: Path,
        release_summary: dict[str, Any],
    ) -> dict[str, Any]:
        failed = bool(audit_report.issues or release_report.errors)
        return {
            "schema_version": 1,
            "slug": slug,
            "title": data.get("title"),
            "formats": formats,
            "config": self._relativizer.relative(config),
            "started_at": self._clock.now().isoformat(),
            "git": self._git.read(),
            "environment": self._tools.environment(),
            "manuscript_audit": {
                "status": audit_report.status,
                "report": self._relativizer.relative(audit_path),
                "counts": audit_report.counts,
                "issues": [asdict(issue) for issue in audit_report.issues],
                "warnings": [asdict(issue) for issue in audit_report.warnings],
            },
            "release_readiness": release_summary,
            "steps": [],
            "artifacts": [],
            "visual_qa": None,
            # The machine can prove render coverage and structural checks. It must leave the
            # literary and visual decision explicit instead of turning a contact sheet into a
            # human approval.
            "human_review": {"status": "pending", "reviewer": None, "notes": []},
            "status": "fail" if failed else "pass",
        }

    def _run_steps(
        self, slug: str, hardcover: bool, report_dir: Path, result: dict[str, Any], strict: bool
    ) -> None:
        for name, command, action in self._steps.plan(slug, hardcover=hardcover, strict=strict):
            step = self._recorder.run(name, command, action, report_dir / f"{name}.log")
            result["steps"].append(step)
            if step["status"] == "fail":
                result["status"] = "fail"
                break

    def _check_artifacts(
        self,
        result: dict[str, Any],
        hardcover: bool,
        hardcover_pdf: Path,
        maximum: int,
        slug: str,
    ) -> None:
        problems = self._inventory.problems(result["artifacts"])
        problems.extend(self._epub_zip.run(self._layout.output / f"{slug}.epub"))
        if hardcover:
            limit = PageLimitCheck(self._pdfs).run(
                hardcover_pdf, label="hardcover interior", maximum=maximum
            )
            if limit:
                problems.append(limit)
        if problems:
            result["status"] = "fail"
            result["problems"] = problems

    def _recheck_release(
        self, result: dict[str, Any], config: Path, pdf: Path, strict: bool, release_path: Path
    ) -> None:
        report = ReleaseAuditor(self._layout.root, self._files, self._pdfs).audit(
            config, pdf=pdf, strict=strict
        )
        self._json.write(release_path, report.as_dict())
        result["release_readiness"] = ReleaseSummary().of(
            report, self._relativizer.relative(release_path)
        )
        if report.errors:
            result["status"] = "fail"

    def _visual_qa(
        self,
        result: dict[str, Any],
        slug: str,
        pdf: Path,
        hardcover_pdf: Path,
        hardcover: bool,
        dpi: int,
    ) -> None:
        try:
            result["visual_qa"] = {}
            variants = [("paperback", pdf)]
            if hardcover:
                variants.append(("hardcover", hardcover_pdf))
            for variant, visual_pdf in variants:
                visual_dir = self._layout.build / slug / "visual-qa" / variant
                visual = self._qa.render(visual_pdf, visual_dir, dpi=dpi)
                self._json.write(
                    visual_dir / "render-report.json", visual.as_dict(), ensure_ascii=True
                )
                result["visual_qa"][variant] = visual.as_dict()
                if visual.unexpected_blank_pages:
                    result["status"] = "fail"
        except (OSError, RuntimeError, ValueError) as error:
            result["status"] = "fail"
            result["visual_qa"] = {"status": "fail", "error": str(error)}
