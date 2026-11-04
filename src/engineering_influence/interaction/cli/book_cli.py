# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `ei book` command group over the shared publishing controller."""

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.controllers.publishing_controller import PublishingController
from engineering_influence.publishing.project_config import ProjectConfig
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError


class BookCli:
    """Audit, build, and publish the books of a project.

    ei book [--root DIR] audit|build|epub|covers|qa|publish ...
    """

    ERRORS = (BookBuildError, ManuscriptError, OSError, ValueError, tomllib.TOMLDecodeError)

    def register(self, subparsers: Any) -> None:
        """Add the `book` command and its subcommands."""
        book = subparsers.add_parser("book", help="audit, build, and publish books")
        book.add_argument("--root", type=Path, default=Path("."), help="project root (default: .)")
        sub = book.add_subparsers(dest="book_command", required=True)
        audit = self._slugs(sub.add_parser("audit", help="manuscript and release-readiness audits"))
        audit.add_argument("--json", action="store_true", help="print the reports as JSON")
        audit.add_argument("--strict-release", action="store_true")
        build = self._slugs(sub.add_parser("build", help="build and verify the interior PDF"))
        build.add_argument(
            "--hardcover", action="store_true", help="the compact hardcover interior"
        )
        build.add_argument("--tex-only", action="store_true", help="write LaTeX only")
        build.add_argument("--no-verify", action="store_true", help="skip the PDF checks")
        epub = self._slugs(sub.add_parser("epub", help="build and verify the EPUB"))
        epub.add_argument("--tex-only", action="store_true", help="write LaTeX only")
        epub.add_argument("--no-verify", action="store_true", help="skip the EPUB checks")
        covers = self._slugs(sub.add_parser("covers", help="build and verify the covers"))
        covers.add_argument("--preview", action="store_true", help="also write small previews")
        covers.add_argument("--hardcover-pdf", type=Path, help="compact hardcover interior")
        qa = sub.add_parser("qa", help="render every page for visual review")
        qa.add_argument("pdf", type=Path)
        qa.add_argument("--output", type=Path)
        qa.add_argument("--dpi", type=int, default=90)
        publish = self._slugs(sub.add_parser("publish", help="the full acceptance pipeline"))
        publish.add_argument("--audit-only", action="store_true")
        publish.add_argument("--no-render", action="store_true", help="skip all-page rendering")
        publish.add_argument("--strict-release", action="store_true")
        publish.add_argument("--dpi", type=int, default=90)
        publish.add_argument("--report-dir", type=Path, help="one report per book below this")

    def run(self, arguments: argparse.Namespace) -> int:
        """Execute the chosen subcommand; return the process status."""
        if arguments.book_command in ("qa", "publish") and arguments.dpi < 36:
            print("error: --dpi must be at least 36", file=sys.stderr)
            return 2
        failures = 0
        try:
            controller = PublishingController(ProjectConfig.load(arguments.root))
            handler = getattr(self, f"_{arguments.book_command}")
            if arguments.book_command == "qa":
                return int(handler(controller, arguments))
            for slug in getattr(arguments, "slugs", None) or controller.book_slugs():
                failures += not self._guarded(handler, controller, slug, arguments)
        except self.ERRORS as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        return 1 if failures else 0

    def _guarded(
        self, handler: Any, controller: PublishingController, slug: str, arguments: Any
    ) -> bool:
        try:
            return bool(handler(controller, slug, arguments))
        except self.ERRORS as error:
            print(f"[{slug}] error: {error}", file=sys.stderr)
            return False

    def _slugs(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("slugs", nargs="*", help="book slugs (default: every configured book)")
        return parser

    def _audit(self, controller: PublishingController, slug: str, arguments: Any) -> bool:
        reports, ok, text = controller.audit(slug, strict_release=arguments.strict_release)
        print(json.dumps(reports, indent=2, ensure_ascii=False) if arguments.json else text)
        return ok

    def _build(self, controller: PublishingController, slug: str, arguments: Any) -> bool:
        print(
            controller.build(
                slug,
                hardcover=arguments.hardcover,
                tex_only=arguments.tex_only,
                verify=not arguments.no_verify,
            )
        )
        return True

    def _epub(self, controller: PublishingController, slug: str, arguments: Any) -> bool:
        print(controller.epub(slug, tex_only=arguments.tex_only, verify=not arguments.no_verify))
        return True

    def _covers(self, controller: PublishingController, slug: str, arguments: Any) -> bool:
        print(
            controller.covers(
                slug, preview=arguments.preview, hardcover_pdf=arguments.hardcover_pdf
            )
        )
        return True

    def _qa(self, controller: PublishingController, arguments: Any) -> int:
        report, ok = controller.qa(arguments.pdf, output=arguments.output, dpi=arguments.dpi)
        print(
            f"rendered {report['rendered_pages']}/{report['page_count']} pages at {report['dpi']} DPI"
        )
        print(f"wrote {len(report['contact_sheets'])} contact sheets under {report['output']}")
        if not ok:
            print(
                f"FAIL blank run exceeds two pages: {report['unexpected_blank_pages']}",
                file=sys.stderr,
            )
            return 1
        print("visual render checks passed")
        return 0

    def _publish(self, controller: PublishingController, slug: str, arguments: Any) -> bool:
        report_path = (
            arguments.report_dir / slug / "publication-report.json"
            if arguments.report_dir
            else None
        )
        result, ok = controller.publish(
            slug,
            dpi=arguments.dpi,
            audit_only=arguments.audit_only,
            no_render=arguments.no_render,
            report_path=report_path,
            strict_release=arguments.strict_release,
        )
        for problem in result.get("problems", []):
            print(f"[{slug}] FAIL {problem}", file=sys.stderr)
        for step in result["steps"]:
            if step["status"] == "fail":
                print(f"[{slug}] FAIL step {step['name']}: see {step['log']}", file=sys.stderr)
        where = (
            report_path or controller.layout.build / slug / "release" / "publication-report.json"
        )
        print(f"[{slug}] publication pipeline {result['status']}; report {where}")
        return ok
