"""Tests inject fakes; they do not patch production code.

Patching the standard library at the system boundary, or a class the test defines itself, is
fine, and the boundary is listed below. Every production class takes its collaborators through its
constructor, so a test passes a fake instead of patching one. A new patch of anything else fails
the first test, and a boundary entry that no test patches any more fails the second until it is
deleted, so the list can only shrink.
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


def test_tests_patch_only_the_system_boundary() -> None:
    unexpected = patched_targets() - BOUNDARY
    assert unexpected == set(), f"inject a fake instead of patching: {sorted(unexpected)}"


def test_the_boundary_list_has_no_stale_entries() -> None:
    stale = BOUNDARY - patched_targets()
    assert stale == set(), (
        f"no test patches these any more; delete them from the list: {sorted(stale)}"
    )
