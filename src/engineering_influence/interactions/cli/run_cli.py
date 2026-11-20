# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``run`` command group: resume or cancel a book run on the stack's database."""

import argparse
import sys
from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.run_cli_interface import RunCliInterface
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.resume_run_interface import ResumeRunInterface

REFUSALS = frozenset({"RUN_NOT_FOUND", "RUN_FINISHED", "RUN_CHANGED"})


class RunCli(RunCliInterface):
    """Exit 0 when the command worked, 1 when the run cannot do what was asked, 2 on setup trouble.

    The services are built on first use, because they need the ``runtime`` extra and the stack's
    settings; a missing extra, a missing setting or an unreachable database prints one line and
    never a traceback that could carry a connection string. If queueing fails after a resume has
    already un-parked the run, running the command again queues the stage.
    """

    def __init__(
        self,
        resume: Callable[[], ResumeRunInterface],
        cancel: Callable[[], CancelRunInterface],
    ) -> None:
        self._resume = resume
        self._cancel = cancel

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``run resume`` and ``run cancel``."""
        run = subparsers.add_parser("run", help="resume or cancel a book run")
        commands = run.add_subparsers(dest="run_command", required=True)
        resume = commands.add_parser("resume", help="continue a parked or stalled run")
        resume.add_argument("run_id")
        cancel = commands.add_parser("cancel", help="stop a run for good")
        cancel.add_argument("run_id")

    def run(self, arguments: argparse.Namespace) -> int:
        """Resume or cancel the named run; return the process status."""
        try:
            if arguments.run_command == "resume":
                resumed = self._resume().resume(arguments.run_id)
                print(
                    f"run {resumed.run_id} is {resumed.status.value} at stage "
                    f"{resumed.stage!r}; its next stage is queued"
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
