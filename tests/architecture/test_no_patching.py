"""Tests inject fakes; they do not patch production code.

Patching the standard library at the system boundary, or a class the test defines itself, is
fine. The production targets listed below are patched only because the class under test builds
them itself, so they cannot be injected yet; each entry says why. A new patch of production code
fails the first test, and removing the last patch of a listed target fails the second until the
entry is deleted, so the list can only shrink.
"""

import ast

from architecture_metrics import REPO

BOUNDARY = {
    "subprocess.run",
    "sys.argv",
    "sys.path",
    "zipfile.ZipFile.testzip",
    "RootPlugin.__init__",
}

AWAITING_INJECTION = {
    "BookBuilder.build": "the controller builds it",
    "PdfVerifier.verify": "the controller and the pipeline steps build it",
    "EbookCoverVerifier.run": "CoverBuilder builds it",
    "KdpCoverSpec.EBOOK_MAX_MB": "its limits are read as class constants",
    "KdpCoverSpec.PDF_MAX_MB": "its limits are read as class constants",
    "KdpCoverSpec.MIN_TEXT_PT": "its limits are read as class constants",
    "engineering_influence.infrastructure.rabbitmq_queue.RabbitMqQueueAdapter.enqueue": (
        "ApiRuntime builds the queue"
    ),
    "engineering_influence.runtime.api_runtime.ApiRuntime.run": "ServeStarter builds the runtime",
    "engineering_influence.runtime.worker_runtime.WorkerRuntime.run": (
        "ServeStarter builds the runtime"
    ),
}


def patched_targets() -> set[str]:
    """What every `monkeypatch.setattr(...)` call in the tests replaces."""
    found: set[str] = set()
    for path in (REPO / "tests").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            is_patch = (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setattr"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "monkeypatch"
                and node.args
            )
            if not is_patch:
                continue
            first = node.args[0]
            target = ast.unparse(first).strip("'\"")
            if len(node.args) > 1 and not isinstance(first, ast.Constant):
                second = node.args[1]
                if isinstance(second, ast.Constant) and isinstance(second.value, str):
                    target += f".{second.value}"
            found.add(target)
    return found


def test_tests_patch_only_the_boundary_and_the_listed_exceptions() -> None:
    unexpected = patched_targets() - BOUNDARY - set(AWAITING_INJECTION)
    assert unexpected == set(), f"inject a fake instead of patching: {sorted(unexpected)}"


def test_the_exception_list_has_no_stale_entries() -> None:
    stale = set(AWAITING_INJECTION) - patched_targets()
    assert stale == set(), (
        f"no test patches these any more; delete them from the list: {sorted(stale)}"
    )
