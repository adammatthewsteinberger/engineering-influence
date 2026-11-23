# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``doctor`` command: check that the model profiles and the web search are ready."""

import argparse
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.doctor_cli_interface import (
    DoctorCliInterface,
)
from engineering_influence.services.interfaces.model_doctor_interface import (
    ModelDoctorInterface,
)
from engineering_influence.services.interfaces.search_doctor_interface import (
    SearchDoctorInterface,
)


class DoctorCli(DoctorCliInterface):
    """``doctor --models`` prints one line per check. Exit 0 when all held, 1 when one failed, 2 on setup trouble.

    By default nothing is sent anywhere. ``--probe`` adds one model-list request per profile and
    never asks a model to complete anything. The doctor is built on first use, because it needs
    the ``runtime`` extra; a missing extra or an unreadable file prints one line and exits
    non-zero, never a traceback.

    ``doctor --search`` sends **one real search request to each configured provider** (SearXNG, then Brave if its key is set),
    with a fixed harmless query unless ``--query`` gives one, and prints one line each. It checks nothing else and runs
    on its own, not with ``--models``.
    """

    DEFAULT_QUERY = "open source book publishing"

    def __init__(
        self,
        doctor: Callable[[bool], ModelDoctorInterface],
        search: Callable[[], SearchDoctorInterface],
        environment: Mapping[str, str],
    ) -> None:
        self._doctor = doctor
        self._search = search
        self._environment = environment

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``doctor --models`` and ``doctor --search``."""
        doctor = subparsers.add_parser("doctor", help="check that this installation is ready")
        what = doctor.add_mutually_exclusive_group(required=True)
        what.add_argument("--models", action="store_true", help="check profiles")
        what.add_argument(
            "--search",
            action="store_true",
            help="run one real search through each configured provider (SearXNG, Brave)",
        )
        doctor.add_argument(
            "--query",
            help=f"the search to run; default: {self.DEFAULT_QUERY!r} (it leaves this machine)",
        )
        doctor.add_argument("--catalog", type=Path, help="default: EI_MODEL_CATALOG")
        doctor.add_argument("--profiles", type=Path, help="default: EI_MODEL_PROFILES")
        doctor.add_argument(
            "--probe",
            action="store_true",
            help="also ask each server to list its models (needs the key; asks no model anything)",
        )

    def run(self, arguments: argparse.Namespace) -> int:
        """Run the checks, print them, and return the process status."""
        if arguments.search:
            return self._run_search(arguments.query or self.DEFAULT_QUERY)
        catalog = arguments.catalog or self._from_environment("EI_MODEL_CATALOG")
        profiles = arguments.profiles or self._from_environment("EI_MODEL_PROFILES")
        if catalog is None or profiles is None:
            print(
                "error: say where the files are: --catalog and --profiles, "
                "or EI_MODEL_CATALOG and EI_MODEL_PROFILES",
                file=sys.stderr,
            )
            return 2
        try:
            findings = self._doctor(arguments.probe).check(catalog, profiles)
        except ImportError as error:
            print(
                "error: doctor needs the runtime extra: "
                f"pip install 'engineering-influence[runtime]' ({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 2
        for finding in findings:
            print(finding.line())
        failed = sum(1 for finding in findings if not finding.passed)
        if failed:
            print(f"{failed} of {len(findings)} checks failed")
            return 1
        sent = "one model-list request per profile" if arguments.probe else "nothing"
        print(f"all {len(findings)} checks passed; sent: {sent}")
        return 0

    def _run_search(self, query: str) -> int:
        try:
            findings = self._search().check(query)
        except ImportError as error:
            print(
                "error: doctor needs the runtime extra: "
                f"pip install 'engineering-influence[runtime]' ({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 2
        for finding in findings:
            print(finding.line())
        failed = sum(1 for finding in findings if not finding.passed)
        if failed:
            print(f"{failed} of {len(findings)} checks failed")
            return 1
        print(f"all {len(findings)} checks passed; sent: one search request per provider")
        return 0

    def _from_environment(self, name: str) -> Path | None:
        value = self._environment.get(name, "").strip()
        return Path(value) if value else None
