# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``run`` command group: look at, resume, cancel or export a book run on the stack's database."""

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from engineering_influence.controllers.interfaces.run_controller_interface import (
    RunControllerInterface,
)
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.run_cli_interface import RunCliInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.services.interfaces.brief_reader_interface import BriefReaderInterface
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.interfaces.export_run_interface import ExportRunInterface
from engineering_influence.services.interfaces.list_runs_interface import ListRunsInterface
from engineering_influence.services.interfaces.resume_run_interface import ResumeRunInterface

REFUSALS = frozenset(
    {
        "RUN_NOT_FOUND",
        "BRIEF_INVALID",
        "BRIEF_UNREADABLE",
        "RUN_KIND_UNSUPPORTED",
        "RUN_FINISHED",
        "RUN_CHANGED",
        "RUN_HAS_NO_ARTIFACTS",
        "EXPORT_TARGET_NOT_EMPTY",
    }
)


class RunCli(RunCliInterface):
    """``status`` prints the run as JSON. Exit 0 when the command worked, 1 when the run cannot do what was asked, 2 on setup trouble.

    The services are built on first use, because they need the ``runtime`` extra and the stack's
    settings; a missing extra, a missing setting or an unreachable database prints one line and
    never a traceback that could carry a connection string. If queueing fails after a resume has
    already un-parked the run, running the command again queues the stage.
    """

    def __init__(
        self,
        resume: Callable[[], ResumeRunInterface],
        cancel: Callable[[], CancelRunInterface],
        status: Callable[[], RunControllerInterface],
        export: Callable[[], ExportRunInterface],
        create: Callable[[], CreateRunInterface],
        listing: Callable[[], ListRunsInterface],
        briefs: BriefReaderInterface,
    ) -> None:
        self._resume = resume
        self._cancel = cancel
        self._status = status
        self._export = export
        self._create = create
        self._listing = listing
        self._briefs = briefs

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``run status``, ``run resume``, ``run cancel`` and ``run export``."""
        run = subparsers.add_parser("run", help="resume or cancel a book run")
        commands = run.add_subparsers(dest="run_command", required=True)
        status = commands.add_parser("status", help="print a run's status as JSON")
        status.add_argument("run_id")
        resume = commands.add_parser("resume", help="continue a parked or stalled run")
        resume.add_argument("run_id")
        cancel = commands.add_parser("cancel", help="stop a run for good")
        cancel.add_argument("run_id")
        export = commands.add_parser(
            "export", help="write a run's book and stage outputs to a new folder"
        )
        export.add_argument("run_id")
        export.add_argument("directory", type=Path, help="a folder that does not exist or is empty")
        create = commands.add_parser(
            "create", help="start a book run from a brief file (TOML) and queue its first stage"
        )
        create.add_argument("brief", type=Path, help="the brief, as TOML")
        commands.add_parser("runs", help="list the saved runs, one line each")

    def _brief(self, path: Path) -> BookBrief:
        """Read a brief file and check it; a file that cannot be read is refused with one line."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            raise ApplicationError(
                code="BRIEF_UNREADABLE",
                message=f"cannot read {path}: {error.strerror}",
                http_status=422,
            ) from error
        return self._briefs.read_text(text, str(path))

    def run(self, arguments: argparse.Namespace) -> int:
        """Resume or cancel the named run; return the process status."""
        try:
            if arguments.run_command == "status":
                summary = self._status().summary(arguments.run_id)
                print(json.dumps(summary.model_dump(mode="json"), sort_keys=True))
            elif arguments.run_command == "resume":
                resumed = self._resume().resume(arguments.run_id)
                print(
                    f"run {resumed.run_id} is {resumed.status.value} at stage "
                    f"{resumed.stage!r}; its next stage is queued"
                )
            elif arguments.run_command == "create":
                brief = self._brief(arguments.brief)
                started = self._create().create(brief)
                print(
                    f"run {started.run_id} is {started.status.value} at stage {started.stage!r}; "
                    "its first stage is queued"
                )
            elif arguments.run_command == "runs":
                for item in self._listing().runs():
                    print(f"{item.run_id}  {item.status.value:<18} {item.stage}")
            elif arguments.run_command == "export":
                done = self._export().export(arguments.run_id, arguments.directory)
                print(
                    f"exported {done.files} files of run {arguments.run_id} to {arguments.directory}: "
                    f"{done.book_files} are the book (books/ and src/), the rest are under run/"
                )
            else:
                cancelled = self._cancel().cancel(arguments.run_id)
                print(f"run {cancelled.run_id} is {cancelled.status.value}")
        except ImportError as error:
            print(
                "error: run needs the runtime extra: "
                f"pip install 'engineering-influence[runtime]' ({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 1 if error.code in REFUSALS else 2
        except Exception as error:  # noqa: BLE001 - one line, never a traceback that could carry a URL
            print(
                f"error: {type(error).__name__} while talking to the stack; run the command again",
                file=sys.stderr,
            )
            return 2
        return 0
