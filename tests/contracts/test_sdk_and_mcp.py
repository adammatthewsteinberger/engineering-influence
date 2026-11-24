"""The SDK's public surface and the MCP server's tools, frozen."""

import inspect
import re
from typing import Any

import engineering_influence_sdk
from engineering_influence_sdk import AsyncEngineeringInfluenceClient, EngineeringInfluenceClient
from snapshot import Snapshot

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.controllers.run_controller import RunController
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.mcp.application import McpApplication
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.list_runs import ListRuns
from engineering_influence.services.read_run import ReadRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.run_management import RunManagement
from engineering_influence.services.start_pipeline import StartPipeline

MODULE_PREFIXES = re.compile(r"\b(typing|collections\.abc|builtins)\.")


def signature(method: Any) -> dict[str, Any]:
    """A method's parameters and return type as data, with the module paths that differ between Python versions removed."""
    found = inspect.signature(method)

    def written(annotation: object) -> str | None:
        if annotation is inspect.Signature.empty:
            return None
        return MODULE_PREFIXES.sub("", inspect.formatannotation(annotation))

    return {
        "parameters": [
            {
                "name": name,
                "kind": parameter.kind.name,
                "annotation": written(parameter.annotation),
                "default": None
                if parameter.default is inspect.Parameter.empty
                else repr(parameter.default),
            }
            for name, parameter in found.parameters.items()
            if name != "self"
        ],
        "returns": written(found.return_annotation),
    }


def surface(client: type) -> dict[str, Any]:
    return {
        name: signature(member)
        for name, member in sorted(inspect.getmembers(client, inspect.isfunction))
        if not name.startswith("_") or name == "__init__"
    }


def test_the_sdk_public_surface_is_frozen() -> None:
    Snapshot("sdk_public_surface").check(
        {
            "exports": sorted(engineering_influence_sdk.__all__),
            "EngineeringInfluenceClient": surface(EngineeringInfluenceClient),
            "AsyncEngineeringInfluenceClient": surface(AsyncEngineeringInfluenceClient),
        }
    )


def test_the_sync_and_async_clients_offer_the_same_operations() -> None:
    assert set(surface(EngineeringInfluenceClient)) == set(surface(AsyncEngineeringInfluenceClient))


def test_the_mcp_tools_and_their_arguments_are_frozen() -> None:
    repo, queue = InMemoryRunRepository(), InMemoryQueue()
    manager = RunManagement(
        ListRuns(repo), ResumeRun(repo, queue), CancelRun(repo), ResolveSpendConsent(repo, queue)
    )
    server: Any = McpApplication(
        ProjectController(StartPipeline(InMemoryLedger(), queue)),
        CreateRun(repo, queue),
        manager,
        RunController(ReadRun(repo, InMemoryArtifactStore())),
        allow_spend=True,
    ).build()
    tools = {
        name: Snapshot.schema(tool.parameters)
        for name, tool in sorted(server._tool_manager._tools.items())
    }
    Snapshot("mcp_tools").check(tools)
