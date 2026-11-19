"""The move map stays complete, consistent and true to the tree while classes move."""

import ast
import tomllib
from collections import Counter
from typing import Any

import pytest
from architecture_metrics import LAYERS, REPO, SOURCE

MAP = REPO / "scripts" / "refactor" / "move_map.toml"
ENTRIES: list[dict[str, Any]] = tomllib.loads(MAP.read_text(encoding="utf-8"))["class"]
KINDS = {"plain", "dataclass", "pydantic", "enum", "exception", "interface", "record"}
STYLES = {"abc", "protocol", "self"}
DECISIONS = {"curated", "signal"}
PUBLIC_API = {
    "Box",
    "BoxBlur",
    "Compositing",
    "CoverLayout",
    "CoverPainter",
    "CoverPlugin",
    "CoverStyle",
    "FilmGrain",
    "Ink",
    "QuietZone",
    "SoftRect",
    "Starfield",
    "ValueNoise",
}


def classes_in(module: str) -> set[str]:
    path = SOURCE.joinpath(*module.split(".")[1:]).with_suffix(".py")
    if not path.exists():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.ClassDef)}


def tree_classes() -> Counter[tuple[str, str]]:
    found: Counter[tuple[str, str]] = Counter()
    for path in SOURCE.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        module = ".".join(
            ("engineering_influence", *path.relative_to(SOURCE).with_suffix("").parts)
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found.update((module, n.name) for n in tree.body if isinstance(n, ast.ClassDef))
    return found


def test_every_entry_is_well_formed() -> None:
    for entry in ENTRIES:
        assert entry["layer"] in LAYERS, entry["old"]
        assert entry["kind"] in KINDS, entry["old"]
        assert entry["interface_style"] in STYLES, entry["old"]
        assert entry["decision"] in DECISIONS, entry["old"]
        assert entry["new"].startswith(f"engineering_influence.{entry['layer']}."), entry["old"]


def test_new_modules_and_class_names_are_unique() -> None:
    assert [k for k, n in Counter(e["new"] for e in ENTRIES).items() if n > 1] == []
    assert [k for k, n in Counter(e["new_name"] for e in ENTRIES).items() if n > 1] == []


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: f"{e['old']}.{e['name']}")
def test_the_class_is_where_the_map_says_it_is(entry: dict[str, Any]) -> None:
    at_old = entry["name"] in classes_in(entry["old"])
    at_new = entry["new_name"] in classes_in(entry["new"])
    assert at_old or at_new, "the class is at neither its old nor its new module"


def test_every_class_in_the_tree_is_in_the_map_exactly_once() -> None:
    mapped: Counter[tuple[str, str]] = Counter()
    for entry in ENTRIES:
        if entry["name"] in classes_in(entry["old"]):
            mapped[(entry["old"], entry["name"])] += 1
        else:
            mapped[(entry["new"], entry["new_name"])] += 1
    assert mapped == tree_classes()


def test_interfaces_pair_with_their_class_by_name_and_location() -> None:
    for entry in ENTRIES:
        if entry["interface_style"] == "self":
            assert entry["interface"] == "" and entry["kind"] == "interface", entry["old"]
            continue
        parent, _, stem = entry["new"].rpartition(".")
        assert entry["interface"] == f"{entry['new_name']}Interface", entry["old"]
        assert entry["interface_module"] == f"{parent}.interfaces.{stem}_interface", entry["old"]
        assert (entry["interface_style"] == "protocol") == (entry["kind"] == "enum"), entry["old"]


def test_the_public_cover_api_is_flagged() -> None:
    flagged = {e["name"] for e in ENTRIES if e.get("public_api")}
    assert flagged == PUBLIC_API
    assert {e["layer"] for e in ENTRIES if e.get("public_api")} <= {
        "models",
        "interfaces",
        "services",
        "infrastructure",
    }
