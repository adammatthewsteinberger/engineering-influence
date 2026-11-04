"""CLI interaction over the shared project controller."""

import argparse
import json

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.services.start_pipeline import StartPipeline


class CliApplication:
    """Runs commands without duplicating domain or service behavior."""

    def run(self, argv: list[str] | None = None) -> int:
        """Parse the command line and return its process status."""
        parser = argparse.ArgumentParser(prog="ei")
        parser.add_argument("--version", action="version", version="engineering-influence 0.1.0a1")
        subparsers = parser.add_subparsers(dest="command")
        pipeline = subparsers.add_parser("pipeline")
        pipeline_subparsers = pipeline.add_subparsers(dest="pipeline_command", required=True)
        start = pipeline_subparsers.add_parser("start")
        start.add_argument("--slug", required=True)
        start.add_argument("--title", required=True)
        start.add_argument("--postulate", action="append", required=True)
        start.add_argument("--stage", action="append")
        arguments = parser.parse_args(argv)
        if arguments.command == "pipeline" and arguments.pipeline_command == "start":
            ledger = InMemoryLedger()
            queue = InMemoryQueue()
            request = ProjectRequest(
                slug=arguments.slug,
                title=arguments.title,
                postulates=tuple(arguments.postulate),
                stages=tuple(arguments.stage or ["thesis"]),
            )
            response = ProjectController(StartPipeline(ledger, queue)).start(request)
            print(json.dumps(response.model_dump(), sort_keys=True))
        return 0


def main() -> None:
    """Console-script shim."""
    raise SystemExit(CliApplication().run())
