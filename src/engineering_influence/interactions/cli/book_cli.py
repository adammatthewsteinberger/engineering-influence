# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `ei book` command group over the shared publishing controller."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.interactions.cli.interfaces.book_cli_interface import BookCliInterface
from engineering_influence.interfaces.keep_awake_interface import KeepAwakeInterface
from engineering_influence.interfaces.local_book_creator_interface import (
    LocalBookCreatorInterface,
)
from engineering_influence.models.bible_card import BibleCard
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.source_entry import SourceEntry

if TYPE_CHECKING:
    from engineering_influence.controllers.publishing_controller import PublishingController


class BookCli(BookCliInterface):
    """Audit, build, and publish the books of a project.

    ei book [--root DIR] audit|build|epub|covers|qa|package|publish ...
    ei book create --kind KIND IDEA --budget-usd N --out DIR --profile FILE
    """

    ERRORS = (BookBuildError, ManuscriptError, OSError, ValueError, tomllib.TOMLDecodeError)

    MICRO = Decimal(1_000_000)

    def __init__(
        self,
        controller_for: Callable[[Path], PublishingController],
        creator_for: Callable[[Path, Mapping[str, str]], LocalBookCreatorInterface],
        keep_awake: KeepAwakeInterface,
        read_sources: Callable[[Path], tuple[SourceEntry, ...]],
        read_bible: Callable[[Path], tuple[BibleCard, ...]],
        read_title: Callable[[Path], str | None],
    ) -> None:
        self._controller_for = controller_for
        self._creator_for = creator_for
        self._keep_awake = keep_awake
        self._read_sources = read_sources
        self._read_bible = read_bible
        self._read_title = read_title

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
        self._slugs(
            sub.add_parser(
                "package",
                help="write the release bundle (listing, manifest, finished files) for KDP",
            )
        )
        create = sub.add_parser(
            "create",
            help="make a whole book from an idea, with nobody in the loop, and write it to a folder",
            description="Runs every stage of the plan for the kind of book (the stages a worker would run, "
            "with the models and search the environment names) and writes the book, its PDF, EPUB, covers, "
            "listing and quality report to --out. The run is kept in a state folder beside it, so a run that "
            "stops can be continued with --resume without paying for finished stages again.",
        )
        create.add_argument("idea", nargs="?", help="what the book is about")
        create.add_argument("--kind", choices=[kind.value for kind in BookKind])
        create.add_argument(
            "--out", type=Path, required=True, help="a new or empty folder for the book"
        )
        create.add_argument(
            "--source",
            type=Path,
            help="a folder of source files (.md, .txt) the run adapts; each file is kept in the run",
        )
        create.add_argument(
            "--bible",
            type=Path,
            help="a bible folder of TOML cards (ADR 0018) the screenplay's scenes draw on by name (screenplay runs only)",
        )
        create.add_argument(
            "--mode",
            choices=["book", "audiobook"],
            default="book",
            help="book (the default) writes a book from an idea; audiobook narrates a finished nonfiction manuscript given with --source, one chapter per file",
        )
        create.add_argument(
            "--stop-after",
            help="stop the run after this stage, for example scene_cards; the stages after it are not run",
        )
        create.add_argument(
            "--previous-lock",
            type=Path,
            help="the shooting_lock.json of an earlier run, so its scene numbers carry over (screenplay runs only)",
        )
        create.add_argument(
            "--budget-usd", help="the most the run may spend, in dollars (no default)"
        )
        create.add_argument("--profile", type=Path, help="the author's details and pricing (TOML)")
        create.add_argument("--title", help="the title to use, if you have one")
        create.add_argument("--audience", help="who the book is for")
        create.add_argument("--target-words", type=int, help="how long the book should be")
        create.add_argument("--trim-size", help="the print trim size, such as 5.5x8.5")
        create.add_argument(
            "--strict-release",
            action="store_true",
            help="fail the build on any release warning; needs [pricing] in the profile",
        )
        create.add_argument(
            "--state-dir", type=Path, help="where the run is kept (default: OUT.state)"
        )
        create.add_argument(
            "--resume", action="store_true", help="continue the run in the state folder"
        )
        create.add_argument(
            "--ignore-estimate",
            action="store_true",
            help="start even if the budget is below what the book is expected to cost",
        )
        create.add_argument(
            "--no-keep-awake",
            action="store_true",
            help="do not hold the computer awake while the book is made",
        )
        create.add_argument(
            "--approve-spend",
            action="store_true",
            help="with --resume: grant the extra budget a stopped run asked for",
        )
        publish = self._slugs(sub.add_parser("publish", help="the full acceptance pipeline"))
        publish.add_argument("--audit-only", action="store_true")
        publish.add_argument("--no-render", action="store_true", help="skip all-page rendering")
        publish.add_argument("--strict-release", action="store_true")
        publish.add_argument("--dpi", type=int, default=90)
        publish.add_argument("--report-dir", type=Path, help="one report per book below this")

    def run(self, arguments: argparse.Namespace) -> int:
        """Execute the chosen subcommand; return the process status."""
        if arguments.book_command == "create":
            return self._create(arguments)
        if arguments.book_command in ("qa", "publish") and arguments.dpi < 36:
            print("error: --dpi must be at least 36", file=sys.stderr)
            return 2
        failures = 0
        try:
            try:
                controller = self._controller_for(arguments.root)
            except ImportError as error:
                # Pillow, numpy and the PDF libraries come with the optional extra; the rest of
                # `ei` (serve, pipeline) must keep working without them.
                print(
                    "error: book commands need the publishing extra: "
                    "pip install 'engineering-influence[publishing]'"
                    f" ({error.name} is missing)",
                    file=sys.stderr,
                )
                return 1
            handler = getattr(self, f"_{arguments.book_command}")
            if arguments.book_command == "qa":
                return int(handler(controller, arguments))
            for slug in getattr(arguments, "slugs", None) or controller.book_slugs():
                failures += not self._guarded(handler, controller, slug, arguments)
        except self.ERRORS as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        return 1 if failures else 0

    def _create(self, arguments: argparse.Namespace) -> int:
        """Make the book: 0 it is written, 1 the run failed, 2 the command could not start, 3 it needs a decision."""
        state = arguments.state_dir or arguments.out.with_name(arguments.out.name + ".state")
        try:
            brief = None if arguments.resume else self._brief(arguments)
            if arguments.resume and not state.is_dir():
                raise ApplicationError(
                    code="LOCAL_RUN_MISSING",
                    message=f"there is no run to resume in {state}",
                    http_status=404,
                )
            if not arguments.resume and state.exists():
                raise ApplicationError(
                    code="LOCAL_RUN_EXISTS",
                    message=f"{state} already holds a run; add --resume to continue it, or choose another --out",
                    http_status=409,
                )
            self._check_out(arguments.out, state, arguments.resume)
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 2
        settings = {"EI_BUILD_STRICT_RELEASE": "1"} if arguments.strict_release else {}
        if arguments.profile is not None:
            settings["EI_AUTHOR_PROFILE"] = str(arguments.profile)
        try:
            creator = self._creator_for(state, settings)
        except ImportError as error:
            print(
                "error: book create needs the runtime and publishing extras: "
                f"pip install 'engineering-influence[runtime,publishing]' ({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 2
        try:
            progress = lambda line: print(line, flush=True)
            if brief is not None and not self._affordable(
                creator, brief, arguments.ignore_estimate
            ):
                return 2
            with self._awake(arguments):
                run = (
                    creator.resume(arguments.approve_spend, progress)
                    if brief is None
                    else creator.start(
                        brief,
                        progress,
                        self._sources(arguments.source),
                        self._previous_lock(arguments.previous_lock),
                        arguments.stop_after,
                        arguments.mode,
                        bible=self._bible(arguments.bible),
                        title=self._title(arguments.source),
                    )
                )
            return self._finish(creator, run, arguments.out, state)
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 2
        finally:
            creator.close()

    @staticmethod
    def _previous_lock(path: Path | None) -> str | None:
        """The previous run's shooting script lock, as text, or none when no lock file was given."""
        return None if path is None else path.read_text(encoding="utf-8")

    def _bible(self, folder: Path | None) -> tuple[BibleCard, ...]:
        """The bible folder's cards, checked, or none when no folder was given."""
        if folder is None:
            return ()
        return self._read_bible(folder)

    def _title(self, folder: Path | None) -> str | None:
        """The source folder's title.toml, checked, or none when there is no folder or no file."""
        if folder is None:
            return None
        return self._read_title(folder)

    def _sources(self, folder: Path | None) -> tuple[SourceEntry, ...]:
        """The folder's source files, numbered and pinned, or none when no folder was given."""
        if folder is None:
            return ()
        return self._read_sources(folder)

    def _awake(self, arguments: argparse.Namespace) -> AbstractContextManager[None]:
        """The keep-awake hold for the run, or nothing when the author asked for none."""
        if arguments.no_keep_awake:
            return nullcontext()
        return self._keep_awake.hold()

    @staticmethod
    def _check_out(out: Path, state: Path, resuming: bool) -> None:
        """Refuse a folder the book could not be written to, before a stage is run, not after the last one.

        The book is written to ``--out`` only when the run ends, and only into a new or empty folder, so a folder
        that holds anything would otherwise be found out after every stage had been run and paid for. A run that
        failed has already written what it made there, so continuing it needs a new folder; the run itself is in
        the state folder and loses nothing.
        """
        if not out.is_symlink() and (not out.exists() or (out.is_dir() and not any(out.iterdir()))):
            return
        advice = (
            f"the run is safe in {state}: continue it into a new folder with "
            f"--out NEW_FOLDER --state-dir {state} --resume"
            if resuming
            else "choose a new or empty --out"
        )
        raise ApplicationError(
            code="EXPORT_TARGET_NOT_EMPTY",
            message=f"{out} already exists and is not an empty folder; {advice}",
            http_status=409,
        )

    def _affordable(
        self, creator: LocalBookCreatorInterface, brief: BookBrief, ignore: bool
    ) -> bool:
        """Say what the book is expected to cost, and refuse a budget that cannot finish it before anything is spent."""
        plan = creator.plan(brief)
        if plan is None:
            return True
        grade = plan.grade()

        def dollars(micro: int) -> str:
            return f"{Decimal(micro) / self.MICRO:.2f}"

        print(
            f"estimate: about {dollars(plan.estimate.expected())} USD for the whole book "
            f"({dollars(plan.estimate.essential())} before editing), against a budget of {dollars(plan.cap)}: {grade}",
            flush=True,
        )
        if grade == plan.SHORT and not ignore:
            print(
                "error: the budget is below what the book is expected to cost before editing. "
                f"Use --budget-usd {dollars(plan.suggested())} or more, or --ignore-estimate to start anyway",
                file=sys.stderr,
            )
            return False
        if grade in (plan.SHORT, plan.TIGHT):
            print("the run may stop to ask for more budget", flush=True)
        elif grade == plan.LEAN:
            print("editing passes that run out of money are skipped; the draft is kept", flush=True)
        return True

    def _finish(
        self, creator: LocalBookCreatorInterface, run: BookRun, out: Path, state: Path
    ) -> int:
        spent = f"spent {Decimal(run.budget.spent) / self.MICRO:.4f} of {Decimal(run.budget.cap) / self.MICRO:.2f} USD"
        if run.status in (RunStatus.AWAITING_CONSENT, RunStatus.PARKED_CAPACITY):
            asked = run.consent.requested_micro_usd if run.consent is not None else None
            need = (
                f"it asked for {Decimal(asked) / self.MICRO:.4f} USD more"
                if asked is not None
                else "it needs more budget"
            )
            print(
                f"stopped at stage {run.stage!r}: {need} ({spent}). Nothing was written to {out}. "
                f"Continue with: ei book create --out {out} --resume --approve-spend",
                file=sys.stderr,
            )
            return 3
        done = creator.export(out)
        for issue in run.issues:
            print(f"issue: {issue.code}: {issue.detail}", file=sys.stderr)
        if run.status is RunStatus.COMPLETED:
            print(
                f"the book is written to {out} ({done.files} files; the finished files are in {out}/run/book); {spent}"
            )
            return 0
        print(
            f"the run {run.status.value} at stage {run.stage!r}; what it made is in {out}; {spent}",
            file=sys.stderr,
        )
        return 1

    def _brief(self, arguments: argparse.Namespace) -> BookBrief:
        for name, value in (
            ("an idea", arguments.idea),
            ("--kind", arguments.kind),
            ("--budget-usd", arguments.budget_usd),
        ):
            if not value:
                raise ApplicationError(
                    code="BRIEF_INVALID",
                    message=f"book create needs {name} (or --resume to continue a run)",
                    http_status=422,
                )
        try:
            micro = int((Decimal(arguments.budget_usd) * self.MICRO).to_integral_value())
        except InvalidOperation as error:
            raise ApplicationError(
                code="BRIEF_INVALID",
                message=f"--budget-usd is a number of dollars, not {arguments.budget_usd!r}",
                http_status=422,
            ) from error
        try:
            return BookBrief(
                kind=BookKind(arguments.kind),
                idea=arguments.idea,
                budget_micro_usd=micro,
                title_hint=arguments.title,
                audience=arguments.audience,
                target_words=arguments.target_words,
                trim_size=arguments.trim_size,
            )
        except ValueError as error:
            raise ApplicationError(
                code="BRIEF_INVALID", message=str(error), http_status=422
            ) from error

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

    def _package(self, controller: PublishingController, slug: str, arguments: Any) -> bool:
        print(controller.package(slug))
        return True

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
