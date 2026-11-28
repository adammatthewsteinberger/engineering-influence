# Made with ❤️ by Vibey.

"""The reference in docs/ names what the code serves: every REST route, every stage a run can take, every contract,
and every error code with the HTTP status it carries."""

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.controllers.run_controller import RunController
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.infrastructure.observability.bootstrap_metrics import BootstrapMetrics
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interactions.api.api_guard import ApiGuard
from engineering_influence.interactions.api.api_observability import ApiObservability
from engineering_influence.interactions.api.application import ApiApplication
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.list_runs import ListRuns
from engineering_influence.services.read_run import ReadRun
from engineering_influence.services.readiness_probe import ReadinessProbe
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.run_management import RunManagement
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.start_pipeline import StartPipeline

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "engineering_influence"
FASTAPI_OWN_ROUTES = {"openapi", "swagger_ui_html", "swagger_ui_redirect", "redoc_html"}
ERROR_ROW = re.compile(r"^\| `([A-Z0-9_]+)` \| ([0-9, ]+) \|$", re.MULTILINE)
Modules = dict[Path, tuple[ast.Module, dict[ast.AST, ast.AST]]]


def docs_text() -> str:
    return "\n".join(
        page.read_text(encoding="utf-8") for page in sorted((ROOT / "docs").glob("*.md"))
    )


def full_app() -> Any:
    """The REST application with every optional part wired in, so every route it can serve is registered."""
    runs, artifacts = InMemoryRunRepository(), InMemoryArtifactStore()
    queue = InMemoryQueue()
    guard = ApiGuard(
        ConstantTimeApiKeyVerifier(["k" * 24]), TokenBucketRateLimiter(burst=10, per_second=10)
    )
    observability = ApiObservability(
        ReadinessProbe(()), BootstrapMetrics(), ContextVarCorrelation()
    )
    return ApiApplication(
        ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue())),
        guard,
        observability=observability,
        runs=RunController(ReadRun(runs, artifacts)),
        creator=CreateRun(InMemoryRunRepository(), InMemoryQueue(), new_id=lambda: "run"),
        manager=RunManagement(
            ListRuns(runs),
            ResumeRun(runs, queue),
            CancelRun(runs),
            ResolveSpendConsent(runs, queue),
        ),
    ).build()


def served_routes(app: Any) -> set[tuple[str, str]]:
    """Each (method, path) the application serves, with FastAPI's own schema and docs pages left out."""
    found: set[tuple[str, str]] = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.name not in FASTAPI_OWN_ROUTES:
            path = route.path.replace(":path}", "}")
            found |= {(method, path) for method in route.methods}
    return found


def test_every_rest_route_is_listed_in_interactions() -> None:
    text = (ROOT / "docs" / "INTERACTIONS.md").read_text(encoding="utf-8")
    missing = sorted(
        f"{method} {path}"
        for method, path in served_routes(full_app())
        if f"`{method} {path}`" not in text
    )
    assert missing == [], f"docs/INTERACTIONS.md does not list these routes: {missing}"


def test_every_stage_a_run_can_take_is_documented() -> None:
    stages = {stage for plan in CreateRun.PLANS.values() for stage in plan.stages}
    text = docs_text()
    missing = sorted(stage for stage in stages if f"`{stage}`" not in text)
    assert missing == [], f"no docs page names these stages: {missing}"


def test_every_contract_class_is_documented() -> None:
    names: set[str] = set()
    for path in (SOURCE / "contracts").rglob("*.py"):
        if "interfaces" in path.parts:
            continue
        names |= {
            node.name
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.ClassDef)
        }
    text = docs_text()
    missing = sorted(name for name in names if name not in text)
    assert missing == [], f"no docs page names these contracts: {missing}"


# ------------------------------------------------------------------------------ error codes and their statuses
def parsed_modules() -> Modules:
    """Every source module's tree, and the parent of each node in it."""
    found: Modules = {}
    for path in sorted(SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        found[path] = (tree, parents)
    return found


def call_name(call: ast.Call) -> str:
    return getattr(call.func, "id", getattr(call.func, "attr", ""))


def enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> Any:
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    return None


def positional_index(function: Any, name: str) -> int | None:
    """Where a parameter sits among the arguments a caller passes by position (self excluded), or None if keyword-only."""
    names = [arg.arg for arg in function.args.args]
    names = names[1:] if names[:1] == ["self"] else names
    return names.index(name) if name in names else None


def literal_values(expr: ast.expr) -> set[object]:
    if isinstance(expr, ast.Constant):
        return {expr.value}
    if isinstance(expr, ast.IfExp):
        return literal_values(expr.body) | literal_values(expr.orelse)
    return set()


def default_values(function: Any, name: str) -> set[object]:
    """The value a parameter takes when a caller leaves it out, or nothing when it has no default."""
    args = function.args
    positional = [arg.arg for arg in args.args]
    if name in positional:
        offset = len(positional) - len(args.defaults)
        index = positional.index(name)
        if index >= offset:
            return literal_values(args.defaults[index - offset])
    keyword = [arg.arg for arg in args.kwonlyargs]
    if name in keyword and args.kw_defaults[keyword.index(name)] is not None:
        return literal_values(args.kw_defaults[keyword.index(name)])
    return set()


def calls_to(
    name: str, param: str, index: int | None, modules: Modules, module: Path
) -> list[tuple[ast.Call, Path]]:
    """The calls to a function named ``name``: in its own module if there are any, otherwise anywhere in the source."""
    own = [
        (c, module)
        for c in ast.walk(modules[module][0])
        if isinstance(c, ast.Call) and call_name(c) == name
    ]
    if own:
        return own
    return [
        (c, path)
        for path, (tree, _) in modules.items()
        for c in ast.walk(tree)
        if isinstance(c, ast.Call)
        and call_name(c) == name
        and (any(k.arg == param for k in c.keywords) or (index is not None and index < len(c.args)))
    ]


def parameter_values(
    function: Any, name: str, module: Path, modules: Modules, depth: int
) -> set[object] | None:
    """What a parameter can be, from every call that passes it or leaves it to its default."""
    index = positional_index(function, name)
    found: set[object] = set()
    for call, call_module in calls_to(function.name, name, index, modules, module):
        given = next((k.value for k in call.keywords if k.arg == name), None)
        if given is None and index is not None and index < len(call.args):
            given = call.args[index]
        if given is None:
            found |= default_values(function, name)
            continue
        values = resolve(
            given,
            enclosing_function(call, modules[call_module][1]),
            call_module,
            modules,
            depth + 1,
        )
        if values is None:
            return None
        found |= values
    return found or None


def assigned_values(
    function: Any, name: str, module: Path, modules: Modules, depth: int
) -> set[object] | None:
    found: set[object] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            values = resolve(node.value, function, module, modules, depth + 1)
            if values is None:
                return None
            found |= values
    return found or None


def final_code_values(modules: Modules) -> set[object] | None:
    """The codes a stage's check can raise: the constants its implementations return, and for an f-string such as
    ``SCREENPLAY_{stage}_INVALID`` one code for each stage of the screenplay plan."""
    stages = ScreenplayRecipes().plan().stages
    found: set[object] = set()
    for tree, _ in modules.values():
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef) and node.name == "final_code"):
                continue
            for ret in ast.walk(node):
                if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Constant):
                    found.add(ret.value.value)
                if isinstance(ret, ast.Return) and isinstance(ret.value, ast.JoinedStr):
                    prefix, suffix = ret.value.values[0].value, ret.value.values[2].value
                    found |= {f"{prefix}{stage.upper()}{suffix}" for stage in stages}
    return found or None


def resolve(
    expr: ast.expr, function: Any, module: Path, modules: Modules, depth: int = 0
) -> set[object] | None:
    """The literal values an expression can take, or None when the test cannot read them from the source."""
    if depth > 6:
        return None
    if isinstance(expr, ast.Constant):
        return {expr.value}
    if isinstance(expr, ast.IfExp):
        body = resolve(expr.body, function, module, modules, depth + 1)
        orelse = resolve(expr.orelse, function, module, modules, depth + 1)
        return None if body is None or orelse is None else body | orelse
    if isinstance(expr, ast.Attribute) and expr.attr == "code":
        return set()  # a code forwarded from a caught error: counted where that error is raised
    if isinstance(expr, ast.Call) and call_name(expr) == "final_code":
        return final_code_values(modules)
    if isinstance(expr, ast.Name) and function is not None:
        if expr.id in [arg.arg for arg in function.args.args + function.args.kwonlyargs]:
            return parameter_values(function, expr.id, module, modules, depth)
        return assigned_values(function, expr.id, module, modules, depth)
    return None


def error_statuses() -> tuple[dict[str, set[int]], list[str]]:
    """Each code the source raises, with the HTTP statuses it can carry, and the raises the test could not read."""
    modules = parsed_modules()
    found: dict[str, set[object]] = defaultdict(set)
    unresolved: list[str] = []
    for path, (tree, parents) in modules.items():
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and call_name(node) == "ApplicationError"):
                continue
            keywords = {k.arg: k.value for k in node.keywords}
            function = enclosing_function(node, parents)
            codes = (
                resolve(keywords["code"], function, path, modules) if "code" in keywords else None
            )
            statuses = (
                resolve(keywords["http_status"], function, path, modules)
                if "http_status" in keywords
                else {400}
            )
            if codes is None or statuses is None:
                unresolved.append(f"{path.relative_to(ROOT)}:{node.lineno}")
                continue
            for code in codes:
                found[str(code)] |= statuses
    return {
        code: {int(status) for status in statuses} for code, statuses in found.items()
    }, unresolved


def documented_error_statuses() -> dict[str, set[int]]:
    text = (ROOT / "docs" / "INTERACTIONS.md").read_text(encoding="utf-8")
    section = text.split("## Error codes\n", 1)[1].split("## REST API\n", 1)[0]
    return {
        code: {int(s) for s in statuses.split(", ")}
        for code, statuses in ERROR_ROW.findall(section)
    }


def test_every_error_raise_in_the_source_has_a_code_and_status_the_test_can_read() -> None:
    _, unresolved = error_statuses()
    assert unresolved == [], (
        f"the code or status of these raises is not readable from the source: {unresolved}"
    )


def test_the_error_code_table_lists_exactly_the_codes_and_statuses_the_source_raises() -> None:
    found, unresolved = error_statuses()
    assert unresolved == []
    documented = documented_error_statuses()
    only_docs = sorted(set(documented) - set(found))
    only_source = sorted(set(found) - set(documented))
    differs = sorted(
        code for code in set(found) & set(documented) if found[code] != documented[code]
    )
    assert not (only_docs or only_source or differs), (
        f"only in docs: {only_docs}; only in source: {only_source}; statuses differ: {differs}"
    )
