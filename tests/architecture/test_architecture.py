"""Structural rules from the architecture plan, enforced on the production tree."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "src" / "engineering_influence"
FILES = sorted(p for p in ROOT.rglob("*.py") if p.name != "__init__.py")

# Allowed outward dependencies per layer (inward-only dependency direction).
FORBIDDEN_IMPORTS = {
    "domain": {
        "contracts",
        "controllers",
        "errors",
        "infrastructure",
        "interaction",
        "interfaces",
        "repositories",
        "services",
    },
    "services": {"controllers", "infrastructure", "interaction", "repositories"},
    "controllers": {"infrastructure", "interaction", "repositories"},
    "interfaces": {"controllers", "infrastructure", "interaction", "repositories", "services"},
}


def layer(path: Path) -> str:
    return path.relative_to(ROOT).parts[0]


def imported_layers(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            if parts[0] == "engineering_influence" and len(parts) > 1:
                found.add(parts[1])
    return found


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_one_class_per_file(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) <= 1, f"{path.name} defines {len(classes)} classes"


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_loose_production_functions(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    loose = [n.name for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    allowed = {"main"} if path.name == "main.py" else set()
    assert set(loose) <= allowed, f"{path.name} has loose functions {loose}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_layer_leaks(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = FORBIDDEN_IMPORTS.get(layer(path), set())
    leaked = imported_layers(tree) & forbidden
    assert not leaked, f"{layer(path)} must not import {sorted(leaked)}"
