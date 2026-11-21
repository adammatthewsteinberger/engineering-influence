# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``doctor`` command: check that the model profiles are ready to be called."""

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


class DoctorCli(DoctorCliInterface):
    """``doctor --models`` prints one line per check. Exit 0 when all held, 1 when one failed, 2 on setup trouble.

    By default nothing is sent anywhere. ``--probe`` adds one model-list request per profile and
    never asks a model to complete anything. The doctor is built on first use, because it needs
    the ``runtime`` extra; a missing extra or an unreadable file prints one line and exits
    non-zero, never a traceback.
    """

    def __init__(
        self,
        doctor: Callable[[bool], ModelDoctorInterface],
        environment: Mapping[str, str],
    ) -> None:
        self._doctor = doctor
        self._environment = environment

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``doctor --models``."""
        doctor = subparsers.add_parser("doctor", help="check that this installation is ready")
        doctor.add_argument("--models", action="store_true", required=True, help="check profiles")
        doctor.add_argument("--catalog", type=Path, help="default: EI_MODEL_CATALOG")
        doctor.add_argument("--profiles", type=Path, help="default: EI_MODEL_PROFILES")
        doctor.add_argument(
            "--probe",
            action="store_true",
            help="also ask each server to list its models (needs the key; asks no model anything)",
        )

    def run(self, arguments: argparse.Namespace) -> int:
        """Run the checks, print them, and return the process status."""
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

    def _from_environment(self, name: str) -> Path | None:
        value = self._environment.get(name, "").strip()
        return Path(value) if value else None
