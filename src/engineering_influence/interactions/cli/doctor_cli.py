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
from engineering_influence.models.doctor_finding import DoctorFinding
from engineering_influence.services.interfaces.local_model_doctor_interface import (
    LocalModelDoctorInterface,
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

    ``doctor --local`` checks the free local model (docs/LOCAL_MODEL.md): the server, the model, one tiny real
    completion (free, and on this machine) and the context size Ollama loaded it with.
    """

    DEFAULT_QUERY = "open source book publishing"

    def __init__(
        self,
        doctor: Callable[[bool], ModelDoctorInterface],
        search: Callable[[], SearchDoctorInterface],
        local: Callable[[], LocalModelDoctorInterface],
        environment: Mapping[str, str],
    ) -> None:
        self._doctor = doctor
        self._search = search
        self._local = local
        self._environment = environment

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``doctor --models``, ``doctor --search`` and ``doctor --local``."""
        doctor = subparsers.add_parser("doctor", help="check that this installation is ready")
        what = doctor.add_mutually_exclusive_group(required=True)
        what.add_argument("--models", action="store_true", help="check profiles")
        what.add_argument(
            "--search",
            action="store_true",
            help="run one real search through each configured provider (SearXNG, Brave)",
        )
        what.add_argument(
            "--local",
            action="store_true",
            help="check the free local model: the server, the model, one tiny answer, the context size",
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
            return self._report(
                lambda: self._search().check(arguments.query or self.DEFAULT_QUERY),
                "one search request per provider",
            )
        if arguments.local:
            return self._report(
                lambda: self._local().check(),
                "one tiny completion to the local model; it stays on this machine",
            )
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

    def _report(self, check: Callable[[], tuple[DoctorFinding, ...]], sent: str) -> int:
        try:
            findings = check()
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
        print(f"all {len(findings)} checks passed; sent: {sent}")
        return 0

    def _from_environment(self, name: str) -> Path | None:
        value = self._environment.get(name, "").strip()
        return Path(value) if value else None
